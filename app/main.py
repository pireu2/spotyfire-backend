"""
SpotyFire Backend - FastAPI Entry Point
Satellite-powered agricultural insurance claims processing.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

from fastapi import Depends

from app.models import (
    AnalyzeRequest, AnalyzeResponse,
    ChatRequest, ChatResponse,
    ReportRequest, ReportResponse
)
from app.data.mocks import DEMO_MODE, MOCK_ANALYSIS_RESPONSE, MOCK_CHAT_CONTEXT
from app.services.ai_agent import chat_with_agent
from app.database import init_db
from app.routes.user import router as user_router
from app.routes.property import router as property_router
from app.services.auth import get_current_user, NeonAuthUser
import app.db_models  # noqa: F401 - Import models so SQLAlchemy creates tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="SpotyFire API",
    description="Satellite-powered agricultural insurance claims processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user_router)
app.include_router(property_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "SpotyFire API",
        "version": "1.0.0",
        "demo_mode": DEMO_MODE
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "demo_mode": DEMO_MODE
    }


# === Analysis Endpoint ===
@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_damage(request: AnalyzeRequest):
    """
    Analyze satellite imagery to detect flood/fire damage.
    
    In DEMO_MODE, returns pre-calculated data for the Galați flood event.
    In production, fetches real Sentinel-1 data and calculates damage.
    """
    if DEMO_MODE:
        # Return mock data for demo/presentation
        return AnalyzeResponse(**MOCK_ANALYSIS_RESPONSE)
    
    # TODO: Implement real satellite analysis
    # This would call the satellite service to:
    # 1. Fetch Sentinel-1 image from 2 weeks ago (before)
    # 2. Fetch Sentinel-1 image from yesterday (after)
    # 3. Calculate pixel difference (change detection)
    # 4. Determine damaged_area_ha and financial_loss
    
    raise HTTPException(
        status_code=501,
        detail="Real satellite analysis not yet implemented. Enable DEMO_MODE."
    )


# === Chat Endpoint ===
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: NeonAuthUser = Depends(get_current_user)):
    """
    Chat with the AI Claims Adjuster (SpotyBot).
    
    Provides context-aware assistance for insurance claims
    using satellite damage analysis data.
    
    Requires authentication.
    """
    context = request.context
    if DEMO_MODE and not context:
        context = MOCK_CHAT_CONTEXT
    
    result = await chat_with_agent(
        message=request.message,
        context=context,
        conversation_history=request.conversation_history
    )
    
    return ChatResponse(**result)


# === Report Generation Endpoint ===
@app.post("/api/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Generate a formal insurance claim PDF.
    
    Creates a downloadable Notice of Loss document with:
    - Map/damage visualization
    - Damage statistics
    - Estimated payout
    - User details
    """
    # TODO: Implement PDF generation service
    # This would call pdf_maker service to generate the document
    
    raise HTTPException(
        status_code=501,
        detail="PDF generation not yet implemented."
    )


# === Development Server ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
