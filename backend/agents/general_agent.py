"""
general_agent.py — ARIA General Assistant Node
Handles weather queries and general conversation.
"""
import json
from agents.state import AgentState
from services.llm import get_voice_llm
from services.llm_utils import call_llm_json
from tools.weather_tool import get_weather

GENERAL_PROMPT = """You are ARIA, a warm EMS paramedic assistant.
Answer the paramedic's general question helpfully and briefly.
You are an admin assistant — NOT a medical advisor.
If asked for clinical guidance, say: "I'm your admin assistant — for clinical guidance, consult your medical director."

Paramedic name: {name}
Question: "{question}"

Respond ONLY with valid JSON: {{"response": "your answer"}}"""

WEATHER_PROMPT = """You are ARIA, a warm EMS paramedic assistant.
Give the paramedic a brief, useful weather summary. Mention anything relevant to EMS operations (ice, heavy rain, visibility).

Paramedic name: {name}
Weather data: {weather_data}

Respond ONLY with valid JSON: {{"response": "weather summary"}}"""


async def general_agent_node(state: AgentState) -> dict:
    paramedic = state.get("paramedic", {})
    messages  = state.get("messages", [])
    intent    = state.get("intent", "general")

    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    name = f"{paramedic.get('first_name', 'Medic')}".strip()

    if intent == "weather":
        weather_data = await get_weather()
        try:
            result = await call_llm_json(
                get_voice_llm(),
                WEATHER_PROMPT.format(name=name, weather_data=json.dumps(weather_data)),
                "Give a weather summary."
            )
            response_text = result.get("response", f"Current weather: {weather_data.get('description', 'N/A')}")
        except Exception:
            response_text = (
                f"It's {weather_data.get('temperature', 'N/A')} and "
                f"{weather_data.get('description', 'conditions unknown')} out there."
            )
        return {
            "active_form": None,
            "display_data": {"weather": weather_data},
            "response_text": response_text,
            "messages": [{"role": "assistant", "content": response_text}],
        }

    # General conversation
    try:
        result = await call_llm_json(
            get_voice_llm(),
            GENERAL_PROMPT.format(name=name, question=last_user_msg),
            last_user_msg,
        )
        response_text = result.get("response", "I'm not sure about that — try asking dispatch.")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[general_agent] LLM failed: {type(e).__name__}: {e}")
        response_text = "I'm not sure about that. Is there anything admin-related I can help with?"

    return {
        "active_form": None,
        "response_text": response_text,
        "messages": [{"role": "assistant", "content": response_text}],
    }
