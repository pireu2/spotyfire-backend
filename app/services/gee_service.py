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
        end_date = ee.Date(date_str).advance(30, 'day')
        collection = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(farm_geom)
                .filterDate(date_str, end_date)
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .select('VV'))
        
        count = collection.size().getInfo()
        print(f"📡 Found {count} Sentinel-1 images for {date_str} (+30 days)")
        
        return collection.mosaic().clip(farm_geom)

    before = get_mosaic(before_date)
    after = get_mosaic(after_date)
    
    before_band_count = before.bandNames().size().getInfo()
    after_band_count = after.bandNames().size().getInfo()
    
    print(f"🔍 Before bands: {before_band_count}, After bands: {after_band_count}")
    
    if before_band_count == 0 or after_band_count == 0:
        error_msg = f"No Sentinel-1 images found for the specified date range. Before: {before_band_count} bands, After: {after_band_count} bands"
        print(f"❌ {error_msg}")
        return {
            "damage_percent": 0.0,
            "damaged_area_ha": 0.0,
            "total_area_ha": 0.0,
            "overlay_b64": "",
            "error": error_msg
        }
    
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
    
    print(f"📊 Analysis Results: Damaged={d_ha:.2f}ha, Total={t_ha:.2f}ha, Percent={pct:.2f}%")
    
    tile_url = change_mask.visualize(palette=['FF0000']).getThumbURL({
        'region': farm_geom,
        'format': 'png',
        'dimensions': 512
    })
    
    print(f"🖼️  Tile URL: {tile_url}")
    
    overlay_b64 = None
    try:
        response = requests.get(tile_url, timeout=30)
        if response.status_code == 200:
            overlay_b64 = base64.b64encode(response.content).decode()
            print(f"✅ Overlay image fetched: {len(overlay_b64)} chars")
        else:
            print(f"❌ Failed to fetch overlay: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to fetch overlay image: {e}")
    
    result = {
        "damageAreaHa": round(d_ha, 2),
        "farmAreaHa": round(t_ha, 2),
        "damagePercent": round(pct, 2),
        "tileUrl": tile_url,
        "overlay_b64": overlay_b64
    }
    
    print(f"📦 Final result: {result['damageAreaHa']}ha damage, overlay={'✅' if overlay_b64 else '❌'}")
    
    return result

async def analyze_property_gee_comparison(
    geometry: Dict,
    incident_date: str,
    cost_per_ha: float = 5000
) -> Dict:
    from datetime import datetime, timedelta
    
    incident_dt = datetime.strptime(incident_date, "%Y-%m-%d")
    before_date = (incident_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    after_date = (incident_dt + timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"📅 Incident Date: {incident_date}")
    print(f"📅 Before Period: {before_date} to {incident_date} (30 days before)")
    print(f"📅 After Period: {incident_date} to {after_date} (30 days after)")
    
    result_before = analyze_farm(geometry, before_date, incident_date)
    result_after = analyze_farm(geometry, incident_date, after_date)
    
    if 'error' in result_before and 'error' in result_after:
        return {
            "damage_percent": 0.0,
            "damaged_area_ha": 0.0,
            "total_area_ha": 0.0,
            "estimated_cost": 0.0,
            "overlay_before_b64": '',
            "overlay_after_b64": '',
            "tile_url": None,
            "analysis_type": "gee_sar_comparison",
            "before_date": before_date,
            "after_date": after_date,
            "incident_date": incident_date,
            "error": "No satellite data available for both periods"
        }
    
    if 'error' in result_before:
        damage_ha = result_after.get('damageAreaHa', 0)
        total_ha = result_after.get('farmAreaHa', 0)
        damage_pct = result_after.get('damagePercent', 0)
        overlay_before_b64 = ''
        overlay_after_b64 = result_after.get('overlay_b64', '')
    elif 'error' in result_after:
        damage_ha = result_before.get('damageAreaHa', 0)
        total_ha = result_before.get('farmAreaHa', 0)
        damage_pct = result_before.get('damagePercent', 0)
        overlay_before_b64 = result_before.get('overlay_b64', '')
        overlay_after_b64 = ''
    else:
        damage_before = result_before.get('damageAreaHa', 0)
        damage_after = result_after.get('damageAreaHa', 0)
        damage_ha = abs(damage_after - damage_before)
        total_ha = result_after.get('farmAreaHa', 0)
        damage_pct = (damage_ha / total_ha * 100) if total_ha > 0 else 0
        overlay_before_b64 = result_before.get('overlay_b64', '')
        overlay_after_b64 = result_after.get('overlay_b64', '')
    
    estimated_cost = damage_ha * cost_per_ha
    
    print(f"📊 Comparison Results: Damage={damage_ha:.2f}ha, Percent={damage_pct:.2f}%")
    
    return {
        "damage_percent": round(damage_pct, 2),
        "damaged_area_ha": round(damage_ha, 2),
        "total_area_ha": round(total_ha, 2),
        "estimated_cost": estimated_cost,
        "overlay_before_b64": overlay_before_b64,
        "overlay_after_b64": overlay_after_b64,
        "tile_url": result_after.get('tileUrl') if 'error' not in result_after else result_before.get('tileUrl'),
        "analysis_type": "gee_sar_comparison",
        "before_date": before_date,
        "after_date": after_date,
        "incident_date": incident_date
    }

async def analyze_property_gee(
    geometry: Dict,
    pre_date: str,
    post_date: str,
    cost_per_ha: float = 5000
) -> Dict:
    result = analyze_farm(geometry, pre_date, post_date)
    
    if 'error' in result:
        return {
            "damage_percent": result.get('damage_percent', 0.0),
            "damaged_area_ha": result.get('damaged_area_ha', 0.0),
            "total_area_ha": result.get('total_area_ha', 0.0),
            "estimated_cost": 0.0,
            "overlay_b64": result.get('overlay_b64', ''),
            "tile_url": None,
            "analysis_type": "gee_sar",
            "error": result['error']
        }
    
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
