"""
delegator.py — ARIA Master Delegator Agent
Classifies every incoming paramedic message into one of 8 intents
and routes to the correct specialist agent node.
"""
from agents.state import AgentState
from services.llm import get_routing_llm
from services.llm_utils import call_llm_json

DELEGATOR_PROMPT = """You are ARIA's routing brain for an EMS paramedic assistant system.

Classify the paramedic's request into EXACTLY ONE of these intents:
- occurrence_report
- teddy_bear
- shift_schedule
- shift_change_request
- status_checklist
- update_checklist
- weather
- general

Classification rules — read carefully and use the MOST SPECIFIC match:
- occurrence_report: ONLY when the paramedic explicitly says they need to FILE or SUBMIT an occurrence/incident report. NOT for questions about compliance or outstanding items.
- teddy_bear: ONLY when the paramedic wants to REQUEST a teddy bear for a patient/child.
- shift_schedule: Any question about schedule, shifts, days, stations, who is working.
- shift_change_request: Any request to change, swap, or request time off from a shift.
- status_checklist: Any question about personal compliance status, outstanding items, missing documents, certifications, ACR/PCR, what is incomplete, what is due. "Outstanding items" = status_checklist.
- update_checklist: ONLY when the paramedic states they have COMPLETED or RESOLVED a specific checklist item (e.g. "I just finished my ACR", "my vaccination was submitted").
- weather: Any question about weather or road conditions.
- general: Anything else.

Respond ONLY with valid JSON, no other text:
{"intent": "...", "summary": "one sentence describing what the paramedic wants"}"""


async def delegator_node(state: AgentState) -> dict:
    """
    Reads the last user message, classifies intent, returns updated state fields.

    IMPORTANT: If a form is already in progress (active_form is set), we skip
    re-classification and stay in that form. The only exception is if the user
    explicitly cancels or uses a clear topic-change phrase.
    """
    messages = state.get("messages", [])
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    if not last_user_message:
        return {
            "intent": "general",
            "intent_summary": "No message provided",
            "response_text": "I didn't catch that. What can I help you with?",
        }

    active_form = state.get("active_form")

    # ── BYPASS DELEGATOR if a form is already in progress ──────────────────
    # Short follow-up answers ("yes", "no", a name, a date, an email) should
    # never be re-classified — they belong to the current form.
    FORM_TO_INTENT = {
        "occurrence_report": "occurrence_report",
        "teddy_bear":        "teddy_bear",
        "shift_change":      "shift_change_request",
    }
    # Explicit cancel/topic-switch keywords — only these break out of a form
    CANCEL_PHRASES = [
        "cancel", "stop", "abort", "forget it", "never mind", "nevermind",
        "start over", "different topic", "new request",
    ]
    user_lower = last_user_message.lower()

    if active_form and FORM_TO_INTENT.get(active_form):
        # Check if the user is explicitly cancelling
        if any(phrase in user_lower for phrase in CANCEL_PHRASES):
            # Cancel — clear form state and re-classify below
            pass
        else:
            # Stay in the current form — skip LLM classification entirely
            return {
                "intent": FORM_TO_INTENT[active_form],
                "intent_summary": f"Continuing {active_form} form",
            }
    # ── END BYPASS ──────────────────────────────────────────────────────────

    try:
        result = await call_llm_json(get_routing_llm(), DELEGATOR_PROMPT, last_user_message)
        intent = result.get("intent", "general")
        summary = result.get("summary", "")
    except Exception:
        intent = "general"
        summary = "Could not classify intent"

    # Map intent → active_form value so we can detect topic switches
    intent_to_form = {
        "occurrence_report":    "occurrence_report",
        "teddy_bear":           "teddy_bear",
        "shift_change_request": "shift_change",
    }
    expected_form = intent_to_form.get(intent)

    # If the user switched topics, clear stale form state
    update: dict = {
        "intent": intent,
        "intent_summary": summary,
    }
    if active_form and active_form != expected_form:
        update["active_form"] = None
        update["form_data"] = {}
        update["required_fields"] = []
        update["missing_fields"] = []
        update["confirmation_pending"] = False
        update["confirmed"] = False
        update["submitted"] = False

    return update
