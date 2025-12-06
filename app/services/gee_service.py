import ee
import os
from google.oauth2 import service_account
from typing import Dict, Optional
import base64
import io
import requests
from PIL import Image

KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.private-key.json')

_initialized = False

def init_gee():
    global _initialized
    if _initialized:
        return True
        
    try:
        if not os.path.exists(KEY_PATH):
            print(f"❌ Key file missing at {KEY_PATH}")
            return False
        
        credentials = service_account.Credentials.from_service_account_file(
            KEY_PATH,
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        ee.Initialize(credentials)
        print("✅ Earth Engine Initialized.")
        _initialized = True
        return True
    except Exception as e:
        print(f"❌ Earth Engine Init Error: {e}")
        return False

def analyze_farm(farm_geojson: Dict, before_date: str, after_date: str) -> Dict:
    if not init_gee():
        raise Exception("Google Earth Engine initialization failed")
    
    def convert_coordinates(coords):
        if isinstance(coords, dict) and 'lat' in coords and 'lng' in coords:
            return [coords['lng'], coords['lat']]
        elif isinstance(coords, list):
            return [convert_coordinates(c) for c in coords]
        return coords
    
    if isinstance(farm_geojson, dict):
        if farm_geojson.get('type') == 'FeatureCollection' and 'features' in farm_geojson:
            geom = ee.FeatureCollection(farm_geojson).geometry()
        elif farm_geojson.get('type') == 'Feature':
            geometry_part = farm_geojson['geometry']
            converted_coords = convert_coordinates(geometry_part.get('coordinates'))
            geometry_converted = {
                'type': geometry_part['type'],
                'coordinates': converted_coords
            }
            geom = ee.Geometry(geometry_converted)
        else:
            geom = ee.Geometry(farm_geojson)
    else:
        raise ValueError("Invalid GeoJSON input")

    romania = ee.FeatureCollection("FAO/GAUL/2015/level0") \
        .filter(ee.Filter.eq('ADM0_NAME', 'Romania')) \
        .geometry()
    
    farm_geom = geom.intersection(romania, ee.ErrorMargin(1))
    
    def get_mosaic(date_str):
        end_date = ee.Date(date_str).advance(10, 'day')
        return (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(farm_geom)
                .filterDate(date_str, end_date)
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .select('VV')
                .mosaic()
                .clip(farm_geom))

    before = get_mosaic(before_date)
    after = get_mosaic(after_date)
    
    ratio = after.divide(before)
    change_mask = ratio.gt(1.3).selfMask()
    
    pixel_area = ee.Image.pixelArea()
    
    d_stats = pixel_area.updateMask(change_mask).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=farm_geom,
        scale=10,
        maxPixels=1e9
    )
    
    t_stats = pixel_area.clip(farm_geom).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=farm_geom,
        scale=10,
        maxPixels=1e9
    )
    
    d_m2 = d_stats.get('area').getInfo() or 0.0
    t_m2 = t_stats.get('area').getInfo() or 0.0
    
    d_ha = d_m2 / 10000.0
    t_ha = t_m2 / 10000.0
    
    pct = (d_ha / t_ha * 100.0) if t_ha > 0 else 0.0
    
    tile_url = change_mask.visualize(palette=['FF0000']).getThumbURL({
        'region': farm_geom,
        'format': 'png',
        'dimensions': 512
    })
    
    overlay_b64 = None
    try:
        response = requests.get(tile_url, timeout=30)
        if response.status_code == 200:
            overlay_b64 = base64.b64encode(response.content).decode()
    except Exception as e:
        print(f"Failed to fetch overlay image: {e}")
    
    return {
        "damageAreaHa": round(d_ha, 2),
        "farmAreaHa": round(t_ha, 2),
        "damagePercent": round(pct, 2),
        "tileUrl": tile_url,
        "overlay_b64": overlay_b64
    }

async def analyze_property_gee(
    geometry: Dict,
    pre_date: str,
    post_date: str,
    cost_per_ha: float = 5000
) -> Dict:
    result = analyze_farm(geometry, pre_date, post_date)
    
    estimated_cost = result['damageAreaHa'] * cost_per_ha
    
    return {
        "damage_percent": result['damagePercent'],
        "damaged_area_ha": result['damageAreaHa'],
        "total_area_ha": result['farmAreaHa'],
        "estimated_cost": estimated_cost,
        "overlay_b64": result.get('overlay_b64'),
        "tile_url": result.get('tileUrl'),
        "analysis_type": "gee_sar"
    }
