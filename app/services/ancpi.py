"""
ANCPI (Agenția Națională de Cadastru și Publicitate Imobiliară) mock service.
In production, this would connect to the real ANCPI API with authorized credentials.
For MVP, we use predefined geometries.
"""
import asyncio
from typing import Optional
from pydantic import BaseModel


class CadastralData(BaseModel):
    numar_cadastral: str
    geometry_type: str
    coordinates: list
    center_lat: float
    center_lng: float
    area_ha: float
    locality: str
    county: str


PREDEFINED_GEOMETRIES = [
    {
        "numar_cadastral": "50001",
        "geometry_type": "Polygon",
        "coordinates": [
            [
                {"lat": 45.7489, "lng": 27.1856},
                {"lat": 45.7512, "lng": 27.1856},
                {"lat": 45.7512, "lng": 27.1923},
                {"lat": 45.7489, "lng": 27.1923},
                {"lat": 45.7489, "lng": 27.1856}
            ]
        ],
        "center_lat": 45.7500,
        "center_lng": 27.1890,
        "area_ha": 12.5,
        "locality": "Galați",
        "county": "Galați"
    },
    {
        "numar_cadastral": "50002",
        "geometry_type": "Polygon",
        "coordinates": [
            [
                {"lat": 46.6234, "lng": 27.7256},
                {"lat": 46.6289, "lng": 27.7256},
                {"lat": 46.6289, "lng": 27.7389},
                {"lat": 46.6234, "lng": 27.7389},
                {"lat": 46.6234, "lng": 27.7256}
            ]
        ],
        "center_lat": 46.6261,
        "center_lng": 27.7322,
        "area_ha": 18.3,
        "locality": "Vaslui",
        "county": "Vaslui"
    },
    {
        "numar_cadastral": "50003",
        "geometry_type": "Polygon",
        "coordinates": [
            [
                {"lat": 44.4268, "lng": 26.1025},
                {"lat": 44.4312, "lng": 26.1025},
                {"lat": 44.4312, "lng": 26.1134},
                {"lat": 44.4268, "lng": 26.1134},
                {"lat": 44.4268, "lng": 26.1025}
            ]
        ],
        "center_lat": 44.4290,
        "center_lng": 26.1080,
        "area_ha": 8.7,
        "locality": "București",
        "county": "Ilfov"
    },
    {
        "numar_cadastral": "50004",
        "geometry_type": "Polygon",
        "coordinates": [
            [
                {"lat": 46.7712, "lng": 23.5912},
                {"lat": 46.7789, "lng": 23.5912},
                {"lat": 46.7789, "lng": 23.6089},
                {"lat": 46.7712, "lng": 23.6089},
                {"lat": 46.7712, "lng": 23.5912}
            ]
        ],
        "center_lat": 46.7750,
        "center_lng": 23.6000,
        "area_ha": 25.2,
        "locality": "Cluj-Napoca",
        "county": "Cluj"
    }
]


async def fetch_cadastral_data(numar_cadastral: str) -> Optional[CadastralData]:
    """
    Fetch cadastral data from ANCPI.
    In MVP mode, returns predefined geometry based on the input number.
    """
    await asyncio.sleep(2.5)
    
    try:
        num = int(numar_cadastral.replace("-", "").replace(" ", ""))
        index = num % len(PREDEFINED_GEOMETRIES)
    except ValueError:
        index = hash(numar_cadastral) % len(PREDEFINED_GEOMETRIES)
    
    geometry_data = PREDEFINED_GEOMETRIES[index].copy()
    geometry_data["numar_cadastral"] = numar_cadastral
    
    return CadastralData(**geometry_data)
