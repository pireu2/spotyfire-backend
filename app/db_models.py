"""
Database models for SpotyFire.
Neon Auth automatically creates neon_auth.users_sync table for user data.
We only need to create our own tables (claims, etc.) that reference users.
"""
from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(String(50), unique=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    location_name = Column(String(255), nullable=True)
    
    crop_type = Column(String(100), nullable=False)
    total_area_ha = Column(Float, nullable=False)
    damaged_area_ha = Column(Float, nullable=False)
    damage_percent = Column(Float, nullable=False)
    value_per_ha = Column(Float, nullable=False)
    financial_loss = Column(Float, nullable=False)
    
    disaster_type = Column(String(50), default="flood")
    status = Column(String(50), default="pending")
    
    analysis_data = Column(JSON, nullable=True)
    satellite_info = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)