"""
checklist_agent.py — ARIA Paramedic Status / Checklist Agent
READ: answers questions about compliance status.
WRITE: updates checklist items when paramedic reports completing something.
"""
import json
from agents.state import AgentState
from services.llm import get_voice_llm, get_extraction_llm
from services.llm_utils import call_llm_json
from tools.db_tools import get_paramedic_status, get_bad_status_items, update_status_item

# Map natural language references to item codes
ITEM_CODE_MAP = {
    "acr":          "ACRc",
    "pcr":          "ACRc",
    "acrc":         "ACRc",
    "ace":          "ACEr",
    "acer":         "ACEr",
    "driver":       "CERT-DL",
    "license":      "CERT-DL",
    "licence":      "CERT-DL",
    "dl":           "CERT-DL",
    "vaccination":  "CERT-Va",
    "vaccine":      "CERT-Va",
    "vacc":         "CERT-Va",
    "education":    "CERT-CE",
    "cme":          "CERT-CE",
    "ce":           "CERT-CE",
    "uniform":      "UNIF",
    "criminal":     "CRIM",
    "crc":          "CRIM",
    "acp":          "ACP",
    "vacation":     "VAC",
    "meal":         "MEALS",
    "meals":        "MEALS",
    "overtime":     "OVER",
    "ot":           "OVER",
}

STATUS_READ_PROMPT = """You are ARIA, a warm EMS paramedic assistant.
Answer the paramedic's question about their compliance status based ONLY on the data below.

STRICT RULES:
- ONLY report information that appears in the status_data JSON — do NOT invent, assume, or hallucinate any items, forms, or actions.
- Do NOT mention occurrence reports, teddy bear forms, shift changes, or any other forms — your ONLY job here is compliance checklist status.
- BAD items are urgent — mention them clearly but calmly
- GOOD items with issue_count > 0 may still be noteworthy (e.g. UNIF credits available)
- Be concise — under 5 sentences
- If everything is good, say so clearly and mention any credits/info worth knowing
- Use natural EMS language — "shift-ready", "outstanding", "cleared"
- End by offering to mark anything as resolved

Paramedic question: "{question}"
Status data: {status_data}

Respond ONLY with valid JSON: {{"response": "your answer"}}"""

UPDATE_EXTRACT_PROMPT = """Extract a checklist update intention from paramedic speech.

Known item codes and their aliases:
ACRc = ACR/PCR completion
ACEr = ACE response
CERT-DL = Driver's license
CERT-Va = Vaccinations
CERT-CE = Continuous education/CME
UNIF = Uniform credits
CRIM = Criminal record check
ACP = ACP status
VAC = Vacation
MEALS = Missed meals
OVER = Overtime

Message: "{message}"

If the paramedic is saying they completed/resolved/finished something, extract:
- item_code: the matching code from above
- new_status: "GOOD"
- new_issue_count: 0 (unless they specify a remaining count)
- notes: any additional notes (optional)

Respond ONLY with valid JSON:
{{"item_code": "...", "new_status": "GOOD", "new_issue_count": 0, "notes": null}}
If nothing to update, return: {{"item_code": null}}"""


async def checklist_agent_node(state: AgentState) -> dict:
    paramedic = state.get("paramedic", {})
    messages  = state.get("messages", [])
    intent    = state.get("intent", "status_checklist")
    form_data = dict(state.get("form_data", {}))

    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    medic_num = paramedic.get("username", "")

    # ── UPDATE INTENT: extract what they want to mark done ────────────────
    if intent == "update_checklist" and last_user_msg:
        try:
            result = await call_llm_json(
                get_extraction_llm(),
                UPDATE_EXTRACT_PROMPT.format(message=last_user_msg),
                last_user_msg,
            )
            item_code = result.get("item_code")

            if item_code:
                all_items = get_paramedic_status(medic_num)
                current = next((i for i in all_items if i["item_code"] == item_code), None)

                if current:
                    # Apply the update immediately — no confirmation needed
                    new_status  = result.get("new_status", "GOOD")
                    issue_count = result.get("new_issue_count", 0)
                    notes       = result.get("notes")

                    update_status_item(medic_num, item_code, new_status, issue_count, notes)

                    # Re-fetch updated status
                    all_items = get_paramedic_status(medic_num)
                    updated   = next((i for i in all_items if i["item_code"] == item_code), None)
                    desc      = updated["item_type"] if updated else item_code

                    response_text = f"Done — {desc} is now marked as complete."
                    bad_remaining = [i for i in all_items if i["status"] == "BAD"]
                    if bad_remaining:
                        names = ", ".join(i["item_type"] for i in bad_remaining)
                        response_text += f" You still have {len(bad_remaining)} item(s) outstanding: {names}."
                    else:
                        response_text += " You're all clear — shift-ready!"

                    return {
                        "confirmation_pending": False,
                        "form_data": {},
                        "display_data": {"status_items": all_items},
                        "response_text": response_text,
                        "messages": [{"role": "assistant", "content": response_text}],
                    }
                else:
                    response_text = f"I don't have a record for {item_code} in your profile. Double check the item name?"
                    return {
                        "response_text": response_text,
                        "messages": [{"role": "assistant", "content": response_text}],
                    }
        except Exception:
            pass

    # ── READ INTENT: fetch and summarise status ────────────────────────────
    all_items = get_paramedic_status(medic_num)
    bad_items = [i for i in all_items if i["status"] == "BAD"]

    try:
        result = await call_llm_json(
            get_voice_llm(),
            STATUS_READ_PROMPT.format(
                question=last_user_msg,
                status_data=json.dumps(all_items),
            ),
            "Summarise the status."
        )
        response_text = result.get("response", "Let me check your status.")
    except Exception:
        if bad_items:
            bad_descriptions = ", ".join(f"{i['item_type']} ({i['issue_count']} outstanding)" for i in bad_items)
            response_text = (
                f"You've got {len(bad_items)} item(s) needing attention: {bad_descriptions}. "
                "Want me to mark any of these as resolved?"
            )
        else:
            response_text = "You're in good shape — everything is green. You're shift-ready."

    return {
        "active_form": None,
        "display_data": {"status_items": all_items},
        "response_text": response_text,
        "messages": [{"role": "assistant", "content": response_text}],
    }
