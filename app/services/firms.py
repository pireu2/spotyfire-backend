import datetime as dt
import io
from typing import Sequence, Optional, List, Dict
import pandas as pd
import requests

class FIRMSClient:
    def __init__(
        self,
        api_key: str,
        source: str = "VIIRS_SNPP_NRT",
        day_range: int = 3,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key or ""
        self.source = source
        self.day_range = max(1, min(int(day_range), 10))
        self.timeout_seconds = timeout_seconds

    def _empty_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=["latitude", "longitude", "confidence", "bright_ti4"]
        )

    def get_active_fires(
        self,
        bbox: Sequence[float],
        end_date: Optional[dt.date] = None,
    ) -> pd.DataFrame:
        if not self.api_key:
            print("FIRMSClient: missing API key, returning mock data.")
            return pd.DataFrame([
                {"latitude": 45.435, "longitude": 27.722, "confidence": "high", "bright_ti4": 320.5},
                {"latitude": 45.441, "longitude": 27.735, "confidence": "nominal", "bright_ti4": 315.2}
            ])

        if len(bbox) != 4:
            raise ValueError(f"bbox must be [west, south, east, north], got: {bbox}")
        
        west, south, east, north = map(float, bbox)
        area_str = f"{west},{south},{east},{north}"

        if end_date is None:
            end_date_obj = dt.date.today()
        elif isinstance(end_date, dt.date):
            end_date_obj = end_date
        else:
            end_date_obj = dt.datetime.strptime(str(end_date), "%Y-%m-%d").date()

        start_date = end_date_obj - dt.timedelta(days=self.day_range - 1)

        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{self.api_key}/{self.source}/{area_str}/{self.day_range}/"
            f"{start_date.strftime('%Y-%m-%d')}"
        )

        try:
            resp = requests.get(url, timeout=self.timeout_seconds)
            resp.raise_for_status()
            
            df = pd.read_csv(io.StringIO(resp.text))
            
            if df.empty:
                return self._empty_frame()
            
            required = ["latitude", "longitude"]
            for col in required:
                if col not in df.columns:
                    return self._empty_frame()
            
            if "confidence" not in df.columns:
                df["confidence"] = "unknown"
            if "bright_ti4" not in df.columns:
                df["bright_ti4"] = 300.0

            return df[["latitude", "longitude", "confidence", "bright_ti4"]]

        except Exception as e:
            print(f"FIRMS API error: {e}, returning mock data")
            return pd.DataFrame([
                {"latitude": 45.435, "longitude": 27.722, "confidence": "high", "bright_ti4": 320.5},
                {"latitude": 45.441, "longitude": 27.735, "confidence": "nominal", "bright_ti4": 315.2}
            ])

async def get_fire_data(bbox: List[float], end_date: str, api_key: str = "") -> List[Dict]:
    client = FIRMSClient(api_key=api_key)
    
    try:
        end_date_obj = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
    except:
        end_date_obj = dt.date.today()
    
    df = client.get_active_fires(bbox, end_date_obj)
    
    fire_points = []
    for _, row in df.iterrows():
        fire_points.append({
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "confidence": str(row["confidence"]),
            "brightness": float(row["bright_ti4"])
        })
    
    return fire_points
