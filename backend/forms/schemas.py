from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────
# OCCURRENCE REPORT
# ─────────────────────────────────────────────

class OccurrenceType(str, Enum):
    vehicle    = "Vehicle Incident"
    patient    = "Patient Related"
    equipment  = "Equipment"
    workplace  = "Workplace"
    other      = "Other"


class OccurrenceReportSchema(BaseModel):
    # Auto-filled — never ask for these
    date: str
    time: str
    report_creator: str
    badge_number: str
    creator_details: str

    # Collected through conversation
    occurrence_type: OccurrenceType
    brief_description: str
    observation: str
    vehicle_number: str
    requested_by: str
    target_email: str

    # Optional fields
    call_number: Optional[str] = None
    action_taken: Optional[str] = None
    other_services_involved: Optional[str] = None
    suggested_resolution: Optional[str] = None

    @field_validator("vehicle_number")
    @classmethod
    def vehicle_number_must_be_4_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit() or len(cleaned) != 4:
            raise ValueError("Unit numbers are 4 digits — could you double check that?")
        return cleaned


# ─────────────────────────────────────────────
# TEDDY BEAR COMFORT PROGRAM
# ─────────────────────────────────────────────

class RecipientType(str, Enum):
    patient    = "Patient"
    family     = "Family"
    bystander  = "Bystander"
    other      = "Other"


class GenderType(str, Enum):
    male              = "Male"
    female            = "Female"
    other             = "Other"
    prefer_not_to_say = "Prefer not to say"


class TeddyBearSchema(BaseModel):
    # Auto-filled
    date_time: str
    primary_medic_first: str
    primary_medic_last: str
    primary_medic_number: str

    # Optional second medic (pulled from DB or manually entered)
    second_medic_first: Optional[str] = None
    second_medic_last: Optional[str] = None
    second_medic_number: Optional[str] = None

    # Collected through conversation
    recipient_age: str
    recipient_gender: GenderType
    recipient_type: RecipientType
    target_email: str


# ─────────────────────────────────────────────
# SHIFT CHANGE REQUEST
# ─────────────────────────────────────────────

class ShiftChangeAction(str, Enum):
    day_off   = "Day Off Request"
    swap      = "Swap Shift"
    vacation  = "Vacation Day"
    other     = "Other"


class ShiftChangeRequestSchema(BaseModel):
    # Pre-filled from session
    first_name: str
    last_name: str
    medic_number: str

    # Collected through conversation
    shift_date: str
    shift_start: str
    shift_end: str
    requested_action: ShiftChangeAction
    notes: Optional[str] = None
