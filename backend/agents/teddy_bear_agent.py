"""
teddy_bear_agent.py — ARIA Teddy Bear Comfort Program Agent
Target: under 60 seconds of conversation.
Most data auto-filled; only asks for recipient details + email.
"""
import json
from datetime import datetime
from agents.state import AgentState
from services.llm import get_extraction_llm, get_voice_llm
from services.llm_utils import call_llm_json
from auth.session import lookup_paramedic_by_number
from forms.schemas import TeddyBearSchema
from forms.renderer import render_teddy_bear_html, render_teddy_bear_xml
from forms.email_sender import send_teddy_bear_form
from tools.db_tools import save_form_submission, update_form_email_status
from pydantic import ValidationError

REQUIRED_FIELDS = [
    "recipient_age",
    "recipient_gender",
    "recipient_type",
    "target_email",
]

EXTRACTION_PROMPT = """You are extracting field values from a paramedic's speech for a Teddy Bear Comfort Program form.

Current collected fields (JSON): {current_data}

The paramedic just said: "{message}"

Extract any of these fields if clearly mentioned:
- second_medic_number: their medic number (e.g. "Team07", "10453")
- second_medic_first: their first name
- second_medic_last: their last name
- has_second_medic: true if they said yes/there was/yes there was, false if they said no/just me/no partner
- recipient_age: approximate age as string (e.g. "7", "about 5", "teenager")
- recipient_gender: one of "Male", "Female", "Other", "Prefer not to say"
- recipient_type: one of "Patient", "Family", "Bystander", "Other"
- target_email: email address

Respond ONLY with valid JSON:
{{"extracted_fields": {{"field_name": "value"}}, "confidence": {{"field_name": "HIGH|MEDIUM|LOW"}}}}
If nothing relevant, return: {{"extracted_fields": {{}}, "confidence": {{}}}}"""

NEXT_QUESTION_PROMPT = """You are ARIA, a warm EMS paramedic assistant logging a Teddy Bear Comfort Program form.
This form should take under 60 seconds total. Be brief and warm.

Current form data: {current_data}
Still need to collect: {missing_fields}
Second medic question answered: {second_medic_answered}
Second medic confirmed present: {has_second_medic}

Rules:
- Ask ONE question at a time
- If second_medic_answered is False → ask "Was there a second paramedic on the call with you?"
- If second_medic_answered is True AND has_second_medic is True AND second_medic_number is missing → ask for their medic number or name
- If second_medic_answered is True AND has_second_medic is True AND second_medic_number present but name missing → ask for their full name
- Otherwise ask for the next missing field from: recipient_age, recipient_gender, recipient_type, target_email
- Be warm — this is a kind gesture
- SHORT — 1-2 sentences max

Respond ONLY with valid JSON: {{"response": "your question"}}"""

CONFIRMATION_PROMPT = """You are ARIA. Quickly confirm this Teddy Bear form before sending.
Be brief and warm. End with "Shall I send this?"

Form: {form_data}

Respond ONLY with valid JSON: {{"response": "confirmation text"}}"""


async def teddy_bear_agent_node(state: AgentState) -> dict:
    paramedic   = state.get("paramedic", {})
    messages    = state.get("messages", [])
    form_data   = dict(state.get("form_data", {}))
    active_form = state.get("active_form")

    # ── INITIALISE on first entry ──────────────────────────────────────────
    if active_form != "teddy_bear":
        now = datetime.now()
        form_data.update({
            "date_time":             now.isoformat(),
            "primary_medic_first":   paramedic.get("first_name", ""),
            "primary_medic_last":    paramedic.get("last_name", ""),
            "primary_medic_number":  paramedic.get("username", ""),
            "second_medic_answered": False,
            "has_second_medic":      None,
        })

    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # ── CONFIRMATION FLOW ──────────────────────────────────────────────────
    if state.get("confirmation_pending") and last_user_msg:
        affirmative = any(w in last_user_msg.lower() for w in
                          ["yes", "yeah", "yep", "correct", "right", "send", "go ahead", "confirm", "ok", "okay"])
        negative    = any(w in last_user_msg.lower() for w in
                          ["no", "wait", "stop", "change", "wrong"])
        if affirmative:
            return {
                "confirmed": True,
                "confirmation_pending": False,
                "active_form": "teddy_bear",
                "form_data": form_data,
            }
        elif negative:
            return {
                "confirmed": False,
                "confirmation_pending": False,
                "active_form": "teddy_bear",
                "form_data": form_data,
                "response_text": "Sure — what needs changing?",
                "messages": [{"role": "assistant", "content": "Sure — what needs changing?"}],
            }

    # ── EXTRACT FIELDS ─────────────────────────────────────────────────────
    if last_user_msg:
        try:
            result = await call_llm_json(
                get_extraction_llm(),
                EXTRACTION_PROMPT.format(
                    current_data=json.dumps(form_data),
                    message=last_user_msg,
                ),
                last_user_msg,
            )
            extracted   = result.get("extracted_fields", {})
            confidence  = result.get("confidence", {})

            # ── Handle second medic yes/no answer ────────────────────────
            if "has_second_medic" in extracted:
                has_sm = extracted["has_second_medic"]
                # Normalise to bool
                if isinstance(has_sm, str):
                    has_sm = has_sm.lower() not in ("false", "no", "0")
                form_data["second_medic_answered"] = True
                form_data["has_second_medic"]      = bool(has_sm)
                if not has_sm:
                    # No second medic — clear any partial data
                    form_data["second_medic_first"]  = None
                    form_data["second_medic_last"]   = None
                    form_data["second_medic_number"] = None

            # ── Handle second medic number provided ───────────────────────
            if extracted.get("second_medic_number"):
                form_data["second_medic_answered"] = True
                form_data["has_second_medic"]      = True
                medic_num = str(extracted["second_medic_number"]).strip()
                found = lookup_paramedic_by_number(medic_num)
                if found:
                    form_data["second_medic_number"] = medic_num
                    form_data["second_medic_first"]  = found["first_name"]
                    form_data["second_medic_last"]   = found["last_name"]
                else:
                    form_data["second_medic_number"] = medic_num
                    # Name not found — will ask next turn

            # ── Handle second medic name provided manually ────────────────
            for field in ("second_medic_first", "second_medic_last"):
                if extracted.get(field) and confidence.get(field, "HIGH") != "LOW":
                    form_data[field] = extracted[field]
                    form_data["second_medic_answered"] = True
                    form_data["has_second_medic"]      = True

            # ── Standard recipient fields ─────────────────────────────────
            for field in ("recipient_age", "recipient_gender", "recipient_type", "target_email"):
                if extracted.get(field) and confidence.get(field, "HIGH") != "LOW":
                    form_data[field] = extracted[field]

        except Exception:
            pass

    # ── SECOND MEDIC: number known but name unknown ────────────────────────
    if (form_data.get("has_second_medic")
            and form_data.get("second_medic_number")
            and not form_data.get("second_medic_first")):
        response_text = (
            f"I couldn't find medic {form_data['second_medic_number']} in the system. "
            "What's their first and last name?"
        )
        return {
            "active_form": "teddy_bear",
            "form_data": form_data,
            "required_fields": REQUIRED_FIELDS,
            "missing_fields": [f for f in REQUIRED_FIELDS if not form_data.get(f)],
            "confirmation_pending": False,
            "response_text": response_text,
            "messages": [{"role": "assistant", "content": response_text}],
        }

    # ── COMPUTE MISSING REQUIRED FIELDS ───────────────────────────────────
    missing = [f for f in REQUIRED_FIELDS if not form_data.get(f)]

    # ── ALL DONE — CONFIRMATION ────────────────────────────────────────────
    if not missing and not state.get("confirmation_pending"):
        try:
            result = await call_llm_json(
                get_voice_llm(),
                CONFIRMATION_PROMPT.format(form_data=json.dumps(form_data)),
                "Confirm the form."
            )
            response_text = result.get("response", "All set — shall I send this?")
        except Exception:
            response_text = (
                f"Got it — bear given to a {form_data.get('recipient_type', 'recipient')}, "
                f"age {form_data.get('recipient_age', '—')}. "
                f"Sending to {form_data.get('target_email', '—')}. Shall I send this?"
            )
        return {
            "active_form": "teddy_bear",
            "form_data": form_data,
            "required_fields": REQUIRED_FIELDS,
            "missing_fields": [],
            "confirmation_pending": True,
            "confirmed": False,
            "response_text": response_text,
            "messages": [{"role": "assistant", "content": response_text}],
        }

    # ── STILL COLLECTING ───────────────────────────────────────────────────
    second_medic_answered = form_data.get("second_medic_answered", False)
    has_second_medic      = form_data.get("has_second_medic", None)

    try:
        result = await call_llm_json(
            get_voice_llm(),
            NEXT_QUESTION_PROMPT.format(
                current_data=json.dumps(form_data),
                missing_fields=missing,
                second_medic_answered=second_medic_answered,
                has_second_medic=has_second_medic,
            ),
            "What to ask next?"
        )
        response_text = result.get("response", "How old was the recipient, roughly?")
    except Exception:
        # Hard-coded fallback ladder
        if not second_medic_answered:
            response_text = "Was there a second paramedic on the call with you?"
        elif has_second_medic and not form_data.get("second_medic_number"):
            response_text = "What's their medic number or name?"
        else:
            fallback = {
                "recipient_age":    "How old was the recipient, roughly?",
                "recipient_gender": "Male, female, other, or prefer not to say?",
                "recipient_type":   "Was this given to a patient, a family member, a bystander, or someone else?",
                "target_email":     "What email should I send the form to?",
            }
            next_field    = missing[0] if missing else "target_email"
            response_text = fallback.get(next_field, "Anything else I need?")

    return {
        "active_form": "teddy_bear",
        "form_data": form_data,
        "required_fields": REQUIRED_FIELDS,
        "missing_fields": missing,
        "confirmation_pending": False,
        "confirmed": False,
        "response_text": response_text,
        "messages": [{"role": "assistant", "content": response_text}],
    }


async def teddy_bear_submit_node(state: AgentState) -> dict:
    """Validate, render HTML + XML, email both, save to DB."""
    paramedic = state.get("paramedic", {})
    form_data = dict(state.get("form_data", {}))

    # Remove internal tracking fields before validation
    form_data.pop("second_medic_answered", None)
    form_data.pop("has_second_medic", None)

    try:
        schema = TeddyBearSchema(**form_data)
    except ValidationError as e:
        bad_field = e.errors()[0].get("loc", ["unknown"])[0]
        error_msg = e.errors()[0].get("msg", "Invalid value")
        return {
            "confirmed": False,
            "confirmation_pending": False,
            "missing_fields": [bad_field],
            "error": error_msg,
            "response_text": f"Hold on — {error_msg}",
            "messages": [{"role": "assistant", "content": f"Hold on — {error_msg}"}],
        }

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    html         = render_teddy_bear_html(schema)
    xml          = render_teddy_bear_xml(schema, timestamp)
    target_email = schema.target_email

    form_id = save_form_submission(
        form_type="teddy_bear",
        submitted_by=paramedic.get("username", "unknown"),
        form_data=form_data,
        emailed_to=target_email,
        email_status="pending",
    )

    try:
        success      = await send_teddy_bear_form(html, xml, form_data, target_email)
        email_status = "sent" if success else "failed"
    except Exception:
        email_status = "failed"
        success      = False

    update_form_email_status(form_id, email_status, target_email)

    if success:
        response_text = f"Done — Teddy Bear form sent to {target_email}. Good work out there."
    else:
        response_text = (
            f"Form is saved but the email didn't go through to {target_email}. "
            "You may want to resend manually."
        )

    return {
        "submitted":           True,
        "active_form":         None,
        "confirmation_pending": False,
        "confirmed":           False,
        "form_data":           {},
        "required_fields":     [],
        "missing_fields":      [],
        "response_text":       response_text,
        "messages":            [{"role": "assistant", "content": response_text}],
    }
