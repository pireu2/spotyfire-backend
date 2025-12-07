"""
AI Agent Service using Groq.
Handles chat interactions and claim assistance.
"""
import os
from groq import Groq
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are SpotyBot, an expert Agricultural Insurance Claims Adjuster AI assistant created by SpotyFire.

Your role is to help farmers who have suffered crop damage from natural disasters (floods, fires, droughts) to:
1. Understand the extent of their damage based on satellite forensic data
2. Draft insurance claims and "Notice of Loss" documents
3. Answer questions about the claims process
4. Provide empathetic but professional support

IMPORTANT CONTEXT:
- You have access to satellite analysis data showing the exact damage to the farmer's land
- You use Sentinel-1 SAR (radar) imagery to detect flooding and damage
- Your damage assessments are scientifically backed by before/after satellite comparison

COMMUNICATION STYLE:
- Be empathetic - these farmers have lost their livelihood
- Be professional - you're helping with legal insurance documents
- Be clear - explain complex terms simply
- Be helpful - proactively suggest next steps

WHEN CALCULATING PAYOUTS:
- Formula: damaged_area_ha × value_per_ha = estimated_payout
- Always show your calculation
- Mention that final payout depends on insurance policy terms

NAVIGATION GUIDANCE:
When users ask about generating reports, satellite analysis, or PDF downloads, inform them that they need to:
- Go to the "Rapoarte" (Reports) section of the dashboard
- There they can select a property, choose date ranges, and generate satellite analysis reports
- PDF reports with damage assessment can be downloaded from that page
Tell them: "Pentru a genera un raport satelit sau descărca PDF, accesează secțiunea 'Rapoarte' din meniul dashboard-ului. Acolo vei putea selecta terenul, perioada de analiză și genera raportul dorit."

If you don't have damage context provided, ask the user to first run a satellite analysis of their land."""


async def generate_report_insights(analysis_data: dict, property_data: dict) -> str:
    prompt = f"""Based on the following satellite analysis data, generate a professional, detailed insurance report insight in Romanian.

PROPERTY INFORMATION:
- Name: {property_data.get('name')}
- Crop Type: {property_data.get('crop_type')}
- Total Area: {analysis_data.get('total_area_ha')} hectares
- Location: {property_data.get('center_lat')}, {property_data.get('center_lng')}

INCIDENT INFORMATION:
- Incident Date: {analysis_data.get('incident_date')}
- Analysis Period Before: {analysis_data.get('before_date')} to {analysis_data.get('incident_date')}
- Analysis Period After: {analysis_data.get('incident_date')} to {analysis_data.get('after_date')}

DAMAGE ASSESSMENT:
- Damaged Area: {analysis_data.get('damaged_area_ha')} hectares
- Damage Percentage: {analysis_data.get('damage_percent')}%
- Estimated Cost: {analysis_data.get('estimated_cost')} RON
- NDVI Before: {analysis_data.get('ndvi_before', 'N/A')}
- NDVI After: {analysis_data.get('ndvi_after', 'N/A')}

Please provide:
1. A professional summary of the incident (2-3 paragraphs)
2. Technical analysis of the satellite data findings
3. Assessment of the damage severity and impact on the crop
4. Recommendations for the insurance claim
5. Environmental and agricultural context

Write in formal Romanian, as this will be included in an official insurance document. Be detailed, professional, and empathetic. The report should be approximately 400-500 words."""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert agricultural insurance adjuster and satellite imagery analyst. Generate detailed, professional insurance reports in Romanian."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating AI insights: {e}")
        return "Analiza AI nu este disponibilă momentan. Vă rugăm să contactați un consultant pentru evaluarea detaliată a daunelor."


def build_context_message(context: Optional[dict]) -> str:
    """Build a context message from analysis data."""
    if not context:
        return ""
    
    context_parts = []
    
    if context.get('properties'):
        properties = context.get('properties', [])
        if properties:
            context_parts.append("\nUSER'S REGISTERED PROPERTIES:")
            for i, prop in enumerate(properties, 1):
                estimated_value = prop.get('estimated_value')
                value_str = f"€{estimated_value:,.2f}" if estimated_value else "N/A"
                context_parts.append(f"""
Property {i}: {prop.get('name', 'Unnamed')}
- Location: {prop.get('center_lat', 'N/A')}, {prop.get('center_lng', 'N/A')}
- Crop Type: {prop.get('crop_type') or 'Not specified'}
- Area: {prop.get('area_ha') or 'N/A'} hectares
- Estimated Value: {value_str}
- Risk Score: {prop.get('risk_score', 0)}/100
- Last Analyzed: {prop.get('last_analysed_at') or 'Never'}""")
    
    if context.get('analyses'):
        analyses = context.get('analyses', [])
        if analyses:
            context_parts.append("\nRECENT SATELLITE ANALYSES:")
            for i, analysis in enumerate(analyses, 1):
                context_parts.append(f"""
Analysis {i}:
- Property: {analysis.get('property_name', 'N/A')}
- Date Range: {analysis.get('date_range_start')} to {analysis.get('date_range_end')}
- Damage: {analysis.get('damage_percent', 0):.2f}%
- Affected Area: {analysis.get('damaged_area_ha', 0):.2f} hectares
- Estimated Cost: €{analysis.get('estimated_cost', 0):,.2f}
- NDVI Before: {analysis.get('ndvi_before', 'N/A')}
- NDVI After: {analysis.get('ndvi_after', 'N/A')}
- Analysis Type: {analysis.get('analysis_type', 'SAR')}
- Created: {analysis.get('created_at', 'N/A')}""")
    
    if context.get('claim_id'):
        context_parts.append(f"""
CURRENT DAMAGE ANALYSIS DATA:
- Claim ID: {context.get('claim_id', 'N/A')}
- Location: {context.get('location', 'N/A')}
- Crop Type: {context.get('crop_type', 'N/A')}
- Total Farm Area: {context.get('total_area_ha', 'N/A')} hectares
- Damaged Area: {context.get('damaged_area_ha', 'N/A')} hectares
- Damage Percentage: {context.get('damage_percent', 'N/A')}%
- Value per Hectare: €{context.get('value_per_ha', 'N/A')}
- Estimated Financial Loss: €{context.get('financial_loss', 0):,.2f}
- Disaster Type: {context.get('disaster_type', 'N/A')}
- Analysis Date: {context.get('analysis_date', 'N/A')}""")
    
    if context.get('report_stats'):
        stats = context.get('report_stats', {})
        context_parts.append(f"""
REPORT STATISTICS:
- Total Reports Generated: {stats.get('total_reports', 0)}
- Reports This Month: {stats.get('reports_this_month', 0)}
- Total Damage Detected: {stats.get('total_damage_ha', 0):.2f} hectares
- Total Estimated Loss: €{stats.get('total_loss', 0):,.2f}
- Average Damage: {stats.get('avg_damage_percent', 0):.2f}%""")
    
    if context.get('alerts'):
        alerts = context.get('alerts', [])
        if alerts:
            context_parts.append("\nACTIVE DISASTER ALERTS:")
            for i, alert in enumerate(alerts, 1):
                distance_info = ""
                if alert.get('distance_km') is not None and alert.get('nearest_property'):
                    distance_info = f" ({alert['distance_km']:.1f}km from {alert['nearest_property']})"
                
                severity_emoji = {
                    'low': '🟡',
                    'medium': '🟠',
                    'high': '🔴',
                    'critical': '⚫'
                }.get(alert.get('severity', 'low'), '')
                
                type_emoji = {
                    'fire': '🔥',
                    'flood': '💧',
                    'ndvi': '🌿',
                    'warning': '⚠️'
                }.get(alert.get('type', 'warning'), '')
                
                context_parts.append(f"""
Alert {i}: {type_emoji} {alert.get('message')}{distance_info}
- Type: {alert.get('type', 'N/A').upper()}
- Severity: {severity_emoji} {alert.get('severity', 'N/A').upper()}
- Location: {alert.get('sector', 'N/A')}
- Coordinates: {alert.get('lat', 'N/A')}, {alert.get('lng', 'N/A')}
- Impact Radius: {alert.get('radius_km', 0):.1f}km
- Created: {alert.get('created_at', 'N/A')}""")
    
    if context_parts:
        context_parts.append("\nAPPLICATION CAPABILITIES:")
        context_parts.append("""
- Satellite Analysis: Generate damage reports using Sentinel-1 SAR imagery
- PDF Reports: Download professional reports with satellite overlays
- Property Management: Track multiple properties and their damage history
- NDVI Monitoring: Vegetation health tracking before and after disasters
- Real-time Alerts: Get notified when disasters are detected near your properties
- Proximity Analysis: See how far disasters are from your land
- Insurance Claims: AI-assisted claim drafting and documentation

Use this data to provide accurate, personalized assistance to the farmer. When the user asks about disasters near their property, use the ACTIVE DISASTER ALERTS section which includes distance calculations.""")
        return "\n".join(context_parts)
    
    return ""
    
    return ""


def build_conversation_history(history: Optional[list]) -> list:
    """Convert conversation history to Gemini format."""
    if not history:
        return []
    
    formatted = []
    for msg in history:
        role = "user" if msg.get("role") == "user" else "model"
        formatted.append({
            "role": role,
            "parts": [msg.get("content", "")]
        })
    return formatted


async def generate_ai_suggested_actions(
    message: str,
    response_text: str,
    context: Optional[dict] = None
) -> list[str]:
    """Generate contextual action suggestions using AI."""
    try:
        
        has_properties = context and context.get('properties')
        has_damage_data = context and context.get('claim_id')
        
        context_info = ""
        if has_properties:
            context_info += "Utilizatorul are proprietăți înregistrate. "
        if has_damage_data:
            context_info += "Există date de analiză a daunelor disponibile. "
        if not has_properties and not has_damage_data:
            context_info = "Utilizatorul nu are încă proprietăți sau analize."
        
        prompt = f"""Bazat pe conversația de mai jos, generează exact 3 acțiuni sugestive scurte în limba română pe care utilizatorul le-ar putea dori să le facă în continuare.

Context: {context_info}

Mesajul utilizatorului: {message}

Răspunsul asistentului: {response_text}

Reguli:
- Returnează DOAR 3 acțiuni, fiecare pe o linie nouă
- Fiecare acțiune să fie scurtă (max 5-6 cuvinte)
- Acțiunile să fie relevante pentru conversație și context
- Să fie în limba română
- Nu include numerotare sau punctuație la început
- Să fie acțiuni concrete pe care utilizatorul le poate face în aplicație

Exemple de acțiuni valide:
- Generează cerere de despăgubire
- Adaugă o proprietate nouă
- Vezi raportul de daune
- Rulează analiză satelitară
- Calculează pierderea totală"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        actions_text = response.choices[0].message.content.strip()
        
        actions = [line.strip().lstrip('•-123456789. ') for line in actions_text.split('\n') if line.strip()]
        actions = [a for a in actions if len(a) > 3 and len(a) < 50]
        
        if len(actions) >= 3:
            return actions[:3]
        
        return get_fallback_actions(context)
        
    except Exception:
        return get_fallback_actions(context)


def get_fallback_actions(context: Optional[dict]) -> list[str]:
    """Fallback suggestions if AI generation fails."""
    has_properties = context and context.get('properties')
    has_damage_data = context and context.get('claim_id')
    
    if has_damage_data:
        return [
            "Generează cerere de despăgubire",
            "Vezi detalii despre daune",
            "Descarcă raportul complet"
        ]
    elif has_properties:
        return [
            "Rulează analiză satelitară",
            "Verifică starea proprietăților",
            "Adaugă o proprietate nouă"
        ]
    else:
        return [
            "Adaugă prima ta proprietate",
            "Explorează funcționalitățile",
            "Contactează suport"
        ]


async def chat_with_agent(
    message: str,
    context: Optional[dict] = None,
    conversation_history: Optional[list] = None
) -> dict:
    """
    Send a message to the AI agent and get a response.
    
    Args:
        message: User's message
        context: Analysis data context (damage stats, etc.)
        conversation_history: Previous messages in the conversation
    
    Returns:
        dict with response, suggested_actions, and optional claim_summary
    """
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT + build_context_message(context)}]
        
        if conversation_history:
            for msg in conversation_history:
                role = "assistant" if msg.get("role") == "model" else "user"
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
        
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        response_text = response.choices[0].message.content
        
        suggested_actions = await generate_ai_suggested_actions(message, response_text, context)
        
        claim_summary = None
        if context and context.get("financial_loss"):
            claim_summary = {
                "estimated_payout": context.get("financial_loss"),
                "damage_percent": context.get("damage_percent"),
                "status": "analysis_complete"
            }
        
        return {
            "response": response_text,
            "suggested_actions": suggested_actions,
            "claim_summary": claim_summary
        }
        
    except Exception as e:
        return {
            "response": f"Îmi pare rău, am întâmpinat o problemă de conectare. Vă rugăm să încercați din nou. Eroare: {str(e)}",
            "suggested_actions": ["Încearcă din nou", "Contactează suport"],
            "claim_summary": None
        }


async def test_agent():
    """Test the AI agent with a sample query."""
    from app.data.mocks import MOCK_CHAT_CONTEXT
    
    result = await chat_with_agent(
        message="What happened to my farm and how much will I get?",
        context=MOCK_CHAT_CONTEXT
    )
    print("Response:", result["response"])
    print("Suggested Actions:", result["suggested_actions"])
    print("Claim Summary:", result["claim_summary"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())
