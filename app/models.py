"""Pydantic models for request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# === Analysis Models ===
class AnalyzeRequest(BaseModel):
    lat: float = Field(..., description="Latitude of the affected area")
    lng: float = Field(..., description="Longitude of the affected area")
    crop_type: str = Field(..., description="Type of crop (e.g., 'wheat', 'corn')")
    value_per_ha: float = Field(..., description="Value per hectare in EUR")


class AnalyzeResponse(BaseModel):
    claim_id: str
    location: dict
    crop_type: str
    total_area_ha: float
    damaged_area_ha: float
    damage_percent: float
    value_per_ha: float
    financial_loss: float
    flood_mask_url: Optional[str] = None
    analysis_date: str
    disaster_type: str = "flood"


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the AI assistant")
    context: Optional[dict] = Field(
        default=None, 
        description="Context data from satellite analysis (damage stats, etc.)"
    )
    conversation_history: Optional[list] = Field(
        default=None,
        description="Previous messages in the conversation"
    )


class ChatResponse(BaseModel):
    response: str
    suggested_actions: Optional[list[str]] = None
    claim_summary: Optional[dict] = None


class UserDetails(BaseModel):
    full_name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    policy_number: Optional[str] = None
    bank_iban: Optional[str] = None


class ReportRequest(BaseModel):
    claim_id: str
    user_details: UserDetails
    analysis_data: Optional[dict] = None


class ReportResponse(BaseModel):
    download_url: str
    filename: str
    generated_at: str
