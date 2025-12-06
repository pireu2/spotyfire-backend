"""
User-related API routes for Neon Auth.
Users are synced to neon_auth.users_sync by Neon Auth automatically.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.services.auth import get_current_user, NeonAuthUser

router = APIRouter(prefix="/api/user", tags=["User"])


class UserProfile(BaseModel):
    id: str
    email: Optional[str]
    name: Optional[str]
    raw: Optional[dict] = None


class ClaimSummary(BaseModel):
    id: str
    claim_id: str
    crop_type: str
    damage_percent: float
    financial_loss: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: NeonAuthUser = Depends(get_current_user)):
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        raw=current_user.raw,
    )


@router.get("/claims")
async def get_user_claims(
    current_user: NeonAuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT id, claim_id, crop_type, damage_percent, financial_loss, status, created_at 
            FROM claims 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC
        """),
        {"user_id": current_user.id}
    )
    claims = result.fetchall()
    
    return [
        {
            "id": str(c[0]),
            "claim_id": c[1],
            "crop_type": c[2],
            "damage_percent": c[3],
            "financial_loss": c[4],
            "status": c[5],
            "created_at": c[6].isoformat() if c[6] else None,
        }
        for c in claims
    ]
