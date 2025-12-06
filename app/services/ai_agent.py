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
    
    return f"""
CURRENT DAMAGE ANALYSIS DATA:
- Claim ID: {context.get('claim_id', 'N/A')}
- Location: {context.get('location', 'N/A')}
- Crop Type: {context.get('crop_type', 'N/A')}
- Total Farm Area: {context.get('total_area_ha', 'N/A')} hectares
- Damaged Area: {context.get('damaged_area_ha', 'N/A')} hectares
- Damage Percentage: {context.get('damage_percent', 'N/A')}%
- Value per Hectare: €{context.get('value_per_ha', 'N/A')}
- Estimated Financial Loss: €{context.get('financial_loss', 'N/A'):,.2f}
- Disaster Type: {context.get('disaster_type', 'N/A')}
- Analysis Date: {context.get('analysis_date', 'N/A')}

Use this data to provide accurate, personalized assistance to the farmer.
"""


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
        # Initialize the model
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT + build_context_message(context)
        )
        
        # Start or continue chat
        history = build_conversation_history(conversation_history)
        chat = model.start_chat(history=history)
        
        # Send message and get response
        response = chat.send_message(message)
        response_text = response.text
        
        # Generate suggested actions based on context
        suggested_actions = generate_suggested_actions(message, context)
        
        # Build claim summary if we have context
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
        # Fallback response if API fails
        return {
            "response": f"I apologize, but I'm having trouble connecting right now. Please try again in a moment. Error: {str(e)}",
            "suggested_actions": ["Try again", "Contact support"],
            "claim_summary": None
        }


def generate_suggested_actions(message: str, context: Optional[dict]) -> list[str]:
    """Generate contextual action suggestions."""
    actions = []
    
    message_lower = message.lower()
    
    if not context:
        actions.append("Run satellite analysis first")
        actions.append("Enter your farm coordinates")
        return actions
    
    # Context-aware suggestions
    if "claim" in message_lower or "file" in message_lower:
        actions.append("Generate claim PDF")
        actions.append("Review damage report")
    
    if "money" in message_lower or "pay" in message_lower or "much" in message_lower:
        actions.append("View detailed breakdown")
        actions.append("Download financial report")
    
    if "document" in message_lower or "need" in message_lower:
        actions.append("Generate Notice of Loss")
        actions.append("Create claim package")
    
    # Default suggestions if none matched
    if not actions:
        actions = [
            "Generate insurance claim",
            "Ask about payout",
            "Download damage report"
        ]
    
    return actions[:3]  # Limit to 3 suggestions


# Quick test function
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
