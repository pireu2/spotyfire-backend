"""
AI Agent Service using Google Generative AI (Gemini).
Handles chat interactions and claim assistance.
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"

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

If you don't have damage context provided, ask the user to first run a satellite analysis of their land."""


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
    
    if context_parts:
        context_parts.append("\nUse this data to provide accurate, personalized assistance to the farmer.")
        return "\n".join(context_parts)
    
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
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        
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

        response = model.generate_content(prompt)
        actions_text = response.text.strip()
        
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
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT + build_context_message(context)
        )
        
        history = build_conversation_history(conversation_history)
        chat = model.start_chat(history=history)
        
        response = chat.send_message(message)
        response_text = response.text
        
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
