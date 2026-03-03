"""
occurrence_agent.py — ARIA Occurrence Report Agent
Guides the paramedic through the EMS Occurrence Report form.
Auto-fills everything possible; asks only what it cannot infer.
"""
import json
from datetime import datetime
from agents.state import AgentState
from services.llm import get_extraction_llm, get_voice_llm
from services.llm_utils import call_llm_json
from forms.schemas import OccurrenceReportSchema
from forms.renderer import render_occurrence_report_html
from forms.email_sender import send_occurrence_report
from tools.db_tools import save_form_submission, update_form_email_status
from pydantic import ValidationError

REQUIRED_FIELDS = [
    "occurrence_type",
    "brief_description",
    "observation",
    "vehicle_number",
    "requested_by",
    "target_email",
]

EXTRACTION_PROMPT = """You are extracting field values from a paramedic's speech for an EMS Occurrence Report.

Current collected fields (JSON): {current_data}

The paramedic just said: "{message}"

Extract any of these fields if mentioned:
- occurrence_type: one of "Vehicle Incident", "Patient Related", "Equipment", "Workplace", "Other"
- brief_description: short summary of what happened
- observation: detailed observation (can reuse brief_description if detailed enough)
- vehicle_number: MUST be exactly 4 digits — extract digits only
- requested_by: who requested this report (name or "self-reported")
- target_email: email address to send the form to
- call_number: call/incident number if mentioned
- action_taken: any immediate action taken
- other_services_involved: fire, police etc if mentioned
- suggested_resolution: any prevention suggestions

For each extracted field, also provide a confidence: "HIGH", "MEDIUM", or "LOW".

Respond ONLY with valid JSON:
{{
  "extracted_fields": {{
    "field_name": "value",
    ...
  }},
  "confidence": {{
    "field_name": "HIGH|MEDIUM|LOW",
    ...
  }}
}}
If nothing relevant was said, return: {{"extracted_fields": {{}}, "confidence": {{}}}}"""

NEXT_QUESTION_PROMPT = """You are ARIA, a warm EMS paramedic assistant helping fill out an Occurrence Report.

Paramedic: {paramedic_name}, Badge {badge_number}
Current form data: {current_data}
Still need to collect: {missing_fields}

Rules:
- Ask for ONLY ONE field at a time — the most important missing one
- Be natural, warm, conversational — like a trusted colleague
- Use EMS terms naturally
- If asking for vehicle_number, say "unit number" not "vehicle number"
- SHORT responses — 1-2 sentences max
- Do NOT list out all missing fields

Ask for the next missing field in a natural way.
Respond ONLY with valid JSON: {{"response": "your question here"}}"""

CONFIRMATION_PROMPT = """You are ARIA, a warm EMS paramedic assistant.
Read back this completed Occurrence Report in a natural, friendly voice — like a colleague confirming details before filing.
Keep it under 5 sentences. End with: "Shall I send this?"

Form data: {form_data}

Respond ONLY with valid JSON: {{"response": "your confirmation readback"}}"""


async def occurrence_agent_node(state: AgentState) -> dict:
    paramedic = state.get("paramedic", {})
    messages   = state.get("messages", [])
    form_data  = dict(state.get("form_data", {}))
    active_form = state.get("active_form")
    confirmed  = state.get("confirmed", False)

    # Initialise form with auto-filled fields on first entry
    if active_form != "occurrence_report":
        now = datetime.now()
        form_data.update({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "report_creator": f"{paramedic.get('first_name', '')} {paramedic.get('last_name', '')}".strip(),
            "badge_number": paramedic.get("badge_number", ""),
            "creator_details": f"Badge {paramedic.get('badge_number', '')}, {paramedic.get('role', 'PCP')}",
        })

    # Get last user message
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # ── CONFIRMATION FLOW ──────────────────────────────────────────────────
    if state.get("confirmation_pending") and last_user_msg:
        affirmative = any(w in last_user_msg.lower() for w in
                          ["yes", "yeah", "yep", "correct", "right", "send", "go ahead", "confirm", "ok", "okay"])
        negative = any(w in last_user_msg.lower() for w in
                       ["no", "wait", "stop", "change", "wrong", "incorrect"])

        if affirmative:
            # ── SUBMIT ────────────────────────────────────────────────────
            return {
                "confirmed": True,
                "confirmation_pending": False,
                "active_form": "occurrence_report",
                "form_data": form_data,
            }
        elif negative:
            return {
                "confirmed": False,
                "confirmation_pending": False,
                "active_form": "occurrence_report",
                "form_data": form_data,
                "response_text": "No problem — what would you like to change?",
                "messages": [{"role": "assistant", "content": "No problem — what would you like to change?"}],
            }

    # ── EXTRACT FIELDS FROM USER MESSAGE ──────────────────────────────────
    if last_user_msg:
        try:
            prompt = EXTRACTION_PROMPT.format(
                current_data=json.dumps(form_data),
                message=last_user_msg,
            )
            result = await call_llm_json(get_extraction_llm(), prompt, last_user_msg)
            extracted = result.get("extracted_fields", {})
            confidence = result.get("confidence", {})

            for field, value in extracted.items():
                if value:
                    # Validate vehicle_number format — must be 4 digits
                    if field == "vehicle_number":
                        digits = "".join(filter(str.isdigit, str(value)))
                        if len(digits) == 4:
                            form_data[field] = digits
                            confidence[field] = confidence.get(field, "HIGH")
                        else:
                            # Invalid — do not store; flag for re-asking
                            pass
                    else:
                        # Only store HIGH/MEDIUM confidence fields
                        if confidence.get(field, "HIGH") != "LOW":
                            form_data[field] = value
        except Exception:
            pass

    # ── COMPUTE MISSING FIELDS ────────────────────────────────────────────
    missing = [f for f in REQUIRED_FIELDS if not form_data.get(f)]

    # ── ALL FIELDS FILLED — CONFIRMATION ─────────────────────────────────
    if not missing and not state.get("confirmation_pending"):
        try:
            result = await call_llm_json(
                VOICE_LLM,
                CONFIRMATION_PROMPT.format(form_data=json.dumps(form_data)),
                "Read back the form and ask for confirmation."
            )
            response_text = result.get("response", "Everything looks good — shall I send this?")
        except Exception:
            response_text = (
                f"Okay — I have an {form_data.get('occurrence_type', 'occurrence')} report "
                f"for unit {form_data.get('vehicle_number', '—')} on {form_data.get('date', '—')}. "
                f"Prepared by {form_data.get('report_creator', '—')}. Shall I send this?"
            )

        return {
            "active_form": "occurrence_report",
            "form_data": form_data,
            "required_fields": REQUIRED_FIELDS,
            "missing_fields": [],
            "confirmation_pending": True,
            "confirmed": False,
            "response_text": response_text,
            "messages": [{"role": "assistant", "content": response_text}],
        }

    # ── STILL COLLECTING — ASK NEXT QUESTION ─────────────────────────────
    try:
        result = await call_llm_json(
            VOICE_LLM,
            NEXT_QUESTION_PROMPT.format(
                paramedic_name=f"{paramedic.get('first_name', '')} {paramedic.get('last_name', '')}".strip(),
                badge_number=paramedic.get("badge_number", ""),
                current_data=json.dumps(form_data),
                missing_fields=missing,
            ),
            "What should ARIA ask next?"
        )
        response_text = result.get("response", "What else can you tell me about the incident?")
    except Exception:
        # Fallback plain questions
        field_questions = {
            "occurrence_type": "Was this a vehicle incident, patient-related, equipment issue, workplace issue, or something else?",
            "brief_description": "Tell me what happened.",
            "observation": "Can you give me more detail on what you observed?",
            "vehicle_number": "What's your unit number?",
            "requested_by": "Is this self-reported, or is a supervisor requesting this?",
            "target_email": "Where should I send the completed form?",
        }
        next_field = missing[0] if missing else "target_email"
        response_text = field_questions.get(next_field, "What else do I need to know?")

    return {
        "active_form": "occurrence_report",
        "form_data": form_data,
        "required_fields": REQUIRED_FIELDS,
        "missing_fields": missing,
        "confirmation_pending": False,
        "confirmed": False,
        "response_text": response_text,
        "messages": [{"role": "assistant", "content": response_text}],
    }


async def occurrence_submit_node(state: AgentState) -> dict:
    """Called when paramedic has confirmed — validate, render, email, save."""
    paramedic = state.get("paramedic", {})
    form_data = dict(state.get("form_data", {}))

    try:
        schema = OccurrenceReportSchema(**form_data)
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

    html = render_occurrence_report_html(schema)
    target_email = schema.target_email

    # Save to DB first
    form_id = save_form_submission(
        form_type="occurrence_report",
        submitted_by=paramedic.get("username", "unknown"),
        form_data=form_data,
        emailed_to=target_email,
        email_status="pending",
    )

    try:
        success = await send_occurrence_report(html, form_data, target_email)
        email_status = "sent" if success else "failed"
    except Exception as ex:
        email_status = "failed"
        success = False

    update_form_email_status(form_id, email_status, target_email)

    if success:
        response_text = (
            f"Done — your occurrence report has been sent to {target_email}. You're good."
        )
    else:
        response_text = (
            f"The form is complete but the email didn't go through. "
            f"Try sending to {target_email} again or contact dispatch directly."
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
