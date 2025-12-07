"""
Alert Notification Service
Periodically checks for alerts near user properties and sends email notifications
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import math
import os
import httpx
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.db_models import Alert, Property
from app.services.email_service import send_alert_email

STACK_PROJECT_ID = os.getenv("STACK_PROJECT_ID")
STACK_SECRET_KEY = os.getenv("STACK_SECRET_SERVER_KEY")


async def get_user_email_from_stack(user_id: str) -> tuple[str, str]:
    """Fetch user email and name from Stack Auth API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.stack-auth.com/api/v1/users/{user_id}",
                headers={
                    "x-stack-secret-server-key": STACK_SECRET_KEY,
                    "x-stack-project-id": STACK_PROJECT_ID,
                    "x-stack-access-type": "server",
                },
                timeout=10.0
            )
            if response.status_code == 200:
                user_data = response.json()
                email = user_data.get("primary_email") or user_data.get("primary_email_auth_method", {}).get("value")
                name = user_data.get("display_name") or user_data.get("client_metadata", {}).get("name") or f"User {user_id[:8]}"
                return email or f"user-{user_id[:8]}@example.com", name
            else:
                error_text = response.text
                print(f"⚠️  Stack Auth API returned {response.status_code} for user {user_id[:8]}: {error_text}")
                return f"user-{user_id[:8]}@example.com", f"User {user_id[:8]}"
    except Exception as e:
        print(f"⚠️  Failed to fetch user data from Stack Auth API: {e}")
        return f"user-{user_id[:8]}@example.com", f"User {user_id[:8]}"


def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


async def check_alerts_for_users():
    """Check all active alerts against all user properties and send notifications"""
    print(f"🔔 [{datetime.now()}] Starting alert notification check...")
    
    async for db in get_db_session():
        try:
            result = await db.execute(
                select(Alert).where(
                    and_(
                        Alert.is_active == 1,
                        Alert.lat.isnot(None),
                        Alert.lng.isnot(None)
                    )
                )
            )
            active_alerts = result.scalars().all()
            
            if not active_alerts:
                print("✅ No active alerts found")
                return
            
            print(f"📡 Found {len(active_alerts)} active alerts")
            
            properties_result = await db.execute(
                select(Property).where(
                    and_(
                        Property.center_lat.isnot(None),
                        Property.center_lng.isnot(None)
                    )
                )
            )
            properties = properties_result.scalars().all()
            
            print(f"🏡 Checking {len(properties)} properties")
            
            user_alerts_map: Dict[str, List[Dict]] = {}
            
            for prop in properties:
                nearby_alerts = []
                
                for alert in active_alerts:
                    distance = calculate_distance_km(
                        prop.center_lat, 
                        prop.center_lng, 
                        alert.lat, 
                        alert.lng
                    )
                    
                    proximity_threshold = alert.radius_km if alert.radius_km else 10.0
                    
                    if distance <= proximity_threshold or distance <= 20.0:
                        nearby_alerts.append({
                            'alert': alert,
                            'property': prop,
                            'distance_km': round(distance, 2),
                            'is_within_radius': distance <= (alert.radius_km or 10.0)
                        })
                
                if nearby_alerts:
                    user_id = str(prop.user_id)
                    if user_id not in user_alerts_map:
                        user_alerts_map[user_id] = []
                    user_alerts_map[user_id].extend(nearby_alerts)
            
            print(f"👥 Found {len(user_alerts_map)} users with nearby alerts")
            
            for user_id, alert_data in user_alerts_map.items():
                try:
                    user_email, user_name = await get_user_email_from_stack(user_id)
                    
                    if user_email and not user_email.endswith("@example.com"):
                        await send_alert_email(user_email, user_name, alert_data)
                        print(f"✉️  Sent alert email to {user_email} ({len(alert_data)} alerts)")
                    else:
                        print(f"⚠️  Skipped user {user_id[:8]} - no valid email")
                except Exception as e:
                    print(f"❌ Failed to send email to user {user_id[:8]}: {e}")
            
            print(f"✅ Alert notification check completed")
            
        except Exception as e:
            print(f"❌ Error during alert check: {e}")
        finally:
            await db.close()


async def start_alert_monitoring():
    """Start the periodic alert monitoring service"""
    interval_minutes = int(os.getenv("ALERT_CHECK_INTERVAL_MINUTES", "10"))
    
    print(f"🚀 Starting Alert Notification Service (checking every {interval_minutes} minutes)")
    
    while True:
        try:
            await check_alerts_for_users()
        except Exception as e:
            print(f"❌ Error in alert monitoring loop: {e}")
        
        await asyncio.sleep(interval_minutes * 60)
