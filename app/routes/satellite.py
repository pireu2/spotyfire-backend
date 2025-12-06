from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

from app.database import get_db
from app.db_models import Property, Geometry, SatelliteAnalysis
from app.services.auth import get_current_user_id
from app.services.satellite import process_sar_damage

router = APIRouter()


class AnalyzeRequest(BaseModel):
    date_range_start: str
    date_range_end: str
    cost_per_ha: Optional[float] = 5000


class AnalysisResponse(BaseModel):
    analysis_id: str
    damage_percent: float
    damaged_area_ha: float
    total_area_ha: float
    estimated_cost: float
    ndvi_before: Optional[float] = None
    ndvi_after: Optional[float] = None
    burn_severity: Optional[float] = None
    overlay_b64: str
    fire_points: Optional[List[dict]] = None
    created_at: datetime


class AnalysisListItem(BaseModel):
    id: str
    damage_percent: float
    damaged_area_ha: float
    estimated_cost: float
    date_range_start: date
    date_range_end: date
    created_at: datetime


@router.post("/properties/{property_id}/analyze", response_model=AnalysisResponse)
async def analyze_property_damage(
    property_id: UUID,
    request: AnalyzeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.user_id == user_id)
    )
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    result = await db.execute(
        select(Geometry).where(Geometry.id == property_obj.geometry_id)
    )
    geometry_obj = result.scalar_one_or_none()
    
    if not geometry_obj:
        raise HTTPException(status_code=404, detail="Geometry not found")
    
    geometry_geojson = {
        "type": "Feature",
        "geometry": {
            "type": geometry_obj.type,
            "coordinates": geometry_obj.coordinates
        },
        "properties": {}
    }
    
    analysis_result = await process_sar_damage(
        geometry=geometry_geojson,
        pre_date=request.date_range_start,
        post_date=request.date_range_end,
        cost_per_ha=request.cost_per_ha
    )
    
    new_analysis = SatelliteAnalysis(
        property_id=property_id,
        analysis_type="sar",
        date_range_start=datetime.strptime(request.date_range_start, "%Y-%m-%d").date(),
        date_range_end=datetime.strptime(request.date_range_end, "%Y-%m-%d").date(),
        damage_percent=analysis_result.get("damage_percent"),
        damaged_area_ha=analysis_result.get("damaged_area_ha"),
        total_area_ha=analysis_result.get("total_area_ha"),
        estimated_cost=analysis_result.get("estimated_cost"),
        ndvi_before=analysis_result.get("ndvi_before"),
        ndvi_after=analysis_result.get("ndvi_after"),
        burn_severity=analysis_result.get("burn_severity"),
        overlay_image_b64=analysis_result.get("overlay_b64"),
        fire_points=None
    )
    
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)
    
    property_obj.last_analysed_at = datetime.utcnow()
    await db.commit()
    
    return AnalysisResponse(
        analysis_id=str(new_analysis.id),
        damage_percent=new_analysis.damage_percent,
        damaged_area_ha=new_analysis.damaged_area_ha,
        total_area_ha=new_analysis.total_area_ha,
        estimated_cost=new_analysis.estimated_cost,
        ndvi_before=new_analysis.ndvi_before,
        ndvi_after=new_analysis.ndvi_after,
        burn_severity=new_analysis.burn_severity,
        overlay_b64=new_analysis.overlay_image_b64,
        fire_points=None,
        created_at=new_analysis.created_at
    )


@router.get("/properties/{property_id}/analyses", response_model=List[AnalysisListItem])
async def get_property_analyses(
    property_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.user_id == user_id)
    )
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    result = await db.execute(
        select(SatelliteAnalysis)
        .where(SatelliteAnalysis.property_id == property_id)
        .order_by(SatelliteAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()
    
    return [
        AnalysisListItem(
            id=str(a.id),
            damage_percent=a.damage_percent,
            damaged_area_ha=a.damaged_area_ha,
            estimated_cost=a.estimated_cost,
            date_range_start=a.date_range_start,
            date_range_end=a.date_range_end,
            created_at=a.created_at
        )
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}/overlay")
async def get_analysis_overlay(
    analysis_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SatelliteAnalysis).where(SatelliteAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = await db.execute(
        select(Property).where(Property.id == analysis.property_id, Property.user_id == user_id)
    )
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Unauthorized")
    
    import base64
    from fastapi.responses import Response
    
    if not analysis.overlay_image_b64:
        raise HTTPException(status_code=404, detail="No overlay image available")
    
    image_data = base64.b64decode(analysis.overlay_image_b64)
    
    return Response(content=image_data, media_type="image/png")
