"""
Mock data for Demo Mode.
Pre-calculated perfect response for the Galați/Vaslui flood event (Romania, 2024).
"""

# Demo Mode Flag - Set to True for presentations!
DEMO_MODE = True

# Mock analysis result for the Romanian floods
MOCK_ANALYSIS_RESPONSE = {
    "claim_id": "SF-2024-GAL-001",
    "location": {
        "lat": 45.8838,
        "lng": 27.9432,
        "region": "Galați County",
        "country": "Romania",
        "locality": "Pechea"
    },
    "crop_type": "wheat",
    "total_area_ha": 150.0,
    "damaged_area_ha": 127.5,
    "damage_percent": 85.0,
    "value_per_ha": 1200.0,
    "financial_loss": 153000.0,
    "flood_mask_url": "/static/flood_mask_galati.png",
    "analysis_date": "2024-09-15",
    "disaster_type": "flood",
    "satellite_info": {
        "source": "Sentinel-1 GRD",
        "before_date": "2024-09-01",
        "after_date": "2024-09-14",
        "resolution_m": 10
    }
}

# Context for the AI agent during demo
MOCK_CHAT_CONTEXT = {
    "claim_id": "SF-2024-GAL-001",
    "damage_percent": 85.0,
    "damaged_area_ha": 127.5,
    "total_area_ha": 150.0,
    "crop_type": "wheat",
    "financial_loss": 153000.0,
    "value_per_ha": 1200.0,
    "disaster_type": "flood",
    "location": "Galați County, Romania",
    "analysis_date": "2024-09-15"
}

# Sample conversation starters
SAMPLE_USER_QUESTIONS = [
    "What happened to my farm?",
    "How much money will I get from insurance?",
    "Can you help me file a claim?",
    "What documents do I need?",
    "When will the flooding damage be assessed officially?"
]
