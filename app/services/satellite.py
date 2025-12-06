from typing import Dict
from app.services.gee_service import analyze_property_gee

async def process_sar_damage(
    geometry: Dict,
    pre_date: str,
    post_date: str,
    cost_per_ha: float = 5000
) -> Dict:
    return await analyze_property_gee(geometry, pre_date, post_date, cost_per_ha)
