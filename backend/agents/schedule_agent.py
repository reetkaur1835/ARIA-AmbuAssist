"""
schedule_agent.py — ARIA Shift Schedule Agent
Queries paramedic_shifts.db and answers schedule questions.
Also handles Shift Change Requests.
"""
import json
import random
from datetime import date, datetime
from agents.state import AgentState
from services.llm import get_voice_llm, get_extraction_llm
from services.llm_utils import call_llm_json
from tools.db_tools import query_shifts
from forms.schemas import ShiftChangeRequestSchema
from forms.renderer import render_shift_change_html
from forms.email_sender import send_shift_change_request
from tools.db_tools import save_form_submission, update_form_email_status
from pydantic import ValidationError

SCR_REQUIRED_FIELDS = ["shift_date", "shift_start", "shift_end", "requested_action"]

SCHEDULE_QUERY_PROMPT = """You are extracting schedule query parameters from a paramedic's speech.

Today's date: {today}
Paramedic medic_number: {medic_number}
Paramedic name: {paramedic_name}

The paramedic asked: "{message}"

Determine what shift data they want. Extract:
- query_type: "own_schedule" | "station_schedule" | "partner_lookup" | "unit_lookup"
- date_from: ISO date string (YYYY-MM-DD) — use today if asking about "next" or "upcoming"
- date_to: ISO date string if asking about a range
- station: station name if asking about a specific station ("Main St.", "Woodgrove", "Bedford", "Coral")
- specific_date: ISO date string if asking about one specific day
- medic_identifier: medic number/ID to look up (use the paramedic's own if asking about their schedule)

Respond ONLY with valid JSON:
{{"query_type": "...", "date_from": "...", "date_to": null, "station": null, "specific_date": null, "medic_identifier": "..."}}"""

SCHEDULE_ANSWER_PROMPT = """You are ARIA, a warm EMS paramedic assistant.
Answer the paramedic's schedule question based on the data below.
Be natural and conversational. If no shifts found, say so clearly.
Keep it brief — under 4 sentences unless showing a multi-day schedule.

Paramedic's question: "{question}"
Shift data from database: {shift_data}
Today: {today}

Respond ONLY with valid JSON: {{"response": "your answer"}}"""

SCR_EXTRACTION_PROMPT = """Extract shift change request fields from paramedic speech.

Current data: {current_data}
Message: "{message}"
Today: {today}

Extract any of:
- shift_date: ISO date (YYYY-MM-DD)
- shift_start: time string e.g. "07:00"
- shift_end: time string e.g. "19:00"
- requested_action: one of "Day Off Request", "Swap Shift", "Vacation Day", "Other"
- notes: any additional notes

Respond ONLY with valid JSON:
{{"extracted_fields": {{"field": "value"}}, "confidence": {{"field": "HIGH|MEDIUM|LOW"}}}}"""

FILLER_OPENERS = [
    "Let me check that quickly",
    "Give me a second to pull that up",
    "Hang tight while I peek at scheduling",
    "One moment while I double-check the roster",
]


def _friendly_date(iso_date: str | None) -> str | None:
    if not iso_date:
        return None
    try:
        parsed = datetime.fromisoformat(iso_date)
        return parsed.strftime("%b %d, %Y")
    except Exception:
        return iso_date


def _build_speculative_phrase(station: str | None, date_hint: str | None, medic_label: str) -> str:
    opener = random.choice(FILLER_OPENERS)
    fragments = []
    if station:
        fragments.append(f"for {station}")
    friendly_date = _friendly_date(date_hint)
    if friendly_date:
        fragments.append(f"on {friendly_date}")
    detail = " and ".join(fragments)
    if detail:
        return f"{opener}, {detail}..."
    if medic_label:
        return f"{opener}, {medic_label}..."
    return f"{opener}..."


def _assemble_chunk_text(chunks: list[dict]) -> str:
    parts = [chunk.get("text", "").strip() for chunk in chunks if chunk.get("text")]
    return " ".join(parts).strip()


async def schedule_agent_node(state: AgentState) -> dict:
    paramedic  = state.get("paramedic", {})
    messages   = state.get("messages", [])
    intent     = state.get("intent", "shift_schedule")
    form_data  = dict(state.get("form_data", {}))
    active_form = state.get("active_form")

    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    today     = date.today().isoformat()
    medic_num = paramedic.get("username", "")
    full_name = f"{paramedic.get('first_name', '')} {paramedic.get('last_name', '')}".strip()

    # ── SHIFT CHANGE REQUEST FLOW ──────────────────────────────────────────
    if intent == "shift_change_request" or active_form == "shift_change":
        if active_form != "shift_change":
            form_data.update({
                "first_name":   paramedic.get("first_name", ""),
                "last_name":    paramedic.get("last_name", ""),
                "medic_number": medic_num,  # kept as prompt label only
            })

        # Confirmation flow
        if state.get("confirmation_pending") and last_user_msg:
            affirmative = any(w in last_user_msg.lower() for w in
                              ["yes", "yeah", "send", "go ahead", "confirm", "ok"])
            if affirmative:
                return {"confirmed": True, "confirmation_pending": False,
                        "active_form": "shift_change", "form_data": form_data}
            else:
                return {
                    "confirmed": False, "confirmation_pending": False,
                    "active_form": "shift_change", "form_data": form_data,
                    "response_text": "No problem — what needs changing?",
                    "messages": [{"role": "assistant", "content": "No problem — what needs changing?"}],
                }

        # Extract fields
        if last_user_msg:
            try:
                result = await call_llm_json(
                    get_extraction_llm(),
                    SCR_EXTRACTION_PROMPT.format(
                        current_data=json.dumps(form_data),
                        message=last_user_msg,
                        today=today,
                    ),
                    last_user_msg,
                )
                for field, value in result.get("extracted_fields", {}).items():
                    if value and result.get("confidence", {}).get(field, "HIGH") != "LOW":
                        form_data[field] = value
            except Exception:
                pass

        missing = [f for f in SCR_REQUIRED_FIELDS if not form_data.get(f)]

        if not missing:
            response_text = (
                f"Got it — {form_data.get('requested_action', 'request')} "
                f"for {form_data.get('shift_date', '—')}, "
                f"{form_data.get('shift_start', '—')} to {form_data.get('shift_end', '—')}. "
                "Shall I send this to scheduling?"
            )
            return {
                "active_form": "shift_change",
                "form_data": form_data,
                "required_fields": SCR_REQUIRED_FIELDS,
                "missing_fields": [],
                "confirmation_pending": True,
                "response_text": response_text,
                "messages": [{"role": "assistant", "content": response_text}],
            }

        field_questions = {
            "shift_date":       "What date is the shift you're requesting for?",
            "shift_start":      "What time does that shift start?",
            "shift_end":        "What time does it end?",
            "requested_action": "Are you requesting a day off, a swap, a vacation day, or something else?",
        }
        next_field = missing[0]
        response_text = field_questions.get(next_field, "Can you give me more details?")

        return {
            "active_form": "shift_change",
            "form_data": form_data,
            "required_fields": SCR_REQUIRED_FIELDS,
            "missing_fields": missing,
            "confirmation_pending": False,
            "response_text": response_text,
            "messages": [{"role": "assistant", "content": response_text}],
        }

    # ── SHIFT SCHEDULE QUERY FLOW ──────────────────────────────────────────
    try:
        query_params = await call_llm_json(
            get_extraction_llm(),
            SCHEDULE_QUERY_PROMPT.format(
                today=today,
                medic_number=medic_num,
                paramedic_name=full_name,
                message=last_user_msg,
            ),
            last_user_msg,
        )
    except Exception:
        query_params = {
            "query_type": "own_schedule",
            "date_from": today,
            "medic_identifier": medic_num,
        }

    medic_id  = query_params.get("medic_identifier") or medic_num
    date_from = query_params.get("specific_date") or query_params.get("date_from") or today
    date_to   = query_params.get("date_to")
    station   = query_params.get("station")

    shifts = await query_shifts(
        medic_identifier=medic_id if query_params.get("query_type") != "station_schedule" else None,
        station=station,
        date_from=date_from,
        date_to=date_to,
        limit=14,
    )

    response_chunks: list[dict] = []
    filler_text = _build_speculative_phrase(
        station or (shifts[0]["station"] if shifts and shifts[0].get("station") else None),
        date_from,
        full_name or medic_num,
    )
    if filler_text:
        response_chunks.append({
            "id": "speculative",
            "type": "speculative",
            "text": filler_text,
            "metadata": {
                "intent": intent,
                "station": station,
                "date_hint": date_from,
            },
        })

    try:
        result = await call_llm_json(
            get_voice_llm(),
            SCHEDULE_ANSWER_PROMPT.format(
                question=last_user_msg,
                shift_data=json.dumps(shifts),
                today=today,
            ),
            "Answer the schedule question."
        )
        response_text = result.get("response", "Let me check that for you.")
    except Exception:
        if shifts:
            next_shift = shifts[0]
            response_text = (
                f"Your next shift is on {next_shift['date']} at {next_shift['station']}, "
                f"{next_shift['start_time']}–{next_shift['end_time']}, unit {next_shift['unit_id']}."
            )
        else:
            response_text = "I couldn't find any upcoming shifts for you in the system."

    response_chunks.append({
        "id": "final",
        "type": "final",
        "text": response_text,
        "metadata": {
            "intent": intent,
            "has_data": bool(shifts),
        },
    })

    combined_response = _assemble_chunk_text(response_chunks) or response_text

    return {
        "active_form": None,
        "response_text": combined_response,
        "display_data": {"shifts": shifts},
        "response_chunks": response_chunks,
        "messages": [{"role": "assistant", "content": combined_response}],
    }


async def schedule_submit_node(state: AgentState) -> dict:
    """Submit shift change request via email."""
    paramedic = state.get("paramedic", {})
    form_data = dict(state.get("form_data", {}))

    try:
        schema = ShiftChangeRequestSchema(**form_data)
    except ValidationError as e:
        error_msg = e.errors()[0].get("msg", "Invalid value")
        return {
            "confirmed": False, "confirmation_pending": False,
            "response_text": f"Hold on — {error_msg}",
            "messages": [{"role": "assistant", "content": f"Hold on — {error_msg}"}],
        }

    html = render_shift_change_html(schema)

    form_id = save_form_submission(
        form_type="shift_change",
        submitted_by=paramedic.get("username", "unknown"),
        form_data=form_data,
        emailed_to="Team0@EffectiveAI.net",
        email_status="pending",
    )

    try:
        success = await send_shift_change_request(html, form_data)
        email_status = "sent" if success else "failed"
    except Exception:
        email_status = "failed"
        success = False

    update_form_email_status(form_id, email_status)

    response_text = (
        "Shift change request sent to scheduling." if success
        else "Saved your request but the email didn't go through — check with your supervisor."
    )

    return {
        "submitted": True,
        "active_form": None,
        "confirmation_pending": False,
        "confirmed": False,
        "form_data": {},
        "required_fields": [],
        "missing_fields": [],
        "response_text": response_text,
        "messages": [{"role": "assistant", "content": response_text}],
    }
