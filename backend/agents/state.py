from typing import TypedDict, Annotated, Optional
import operator


class AgentState(TypedDict):
    # Core
    messages: Annotated[list, operator.add]     # [{role: str, content: str}]
    session_id: str
    paramedic: Optional[dict]                   # Authenticated paramedic from aria.db

    # Routing
    intent: Optional[str]                       # Set by delegator node
    intent_summary: Optional[str]               # Human-readable summary

    # Form state
    active_form: Optional[str]                  # "occurrence_report" | "teddy_bear" | "shift_change"
    form_data: dict                             # All field values collected so far
    required_fields: list                       # Must be filled before submit allowed
    missing_fields: list                        # Not yet collected
    confidence_scores: dict                     # field_name -> "HIGH"|"MEDIUM"|"LOW"

    # Flow control
    confirmation_pending: bool                  # Waiting for paramedic yes/no
    confirmed: bool                             # Paramedic approved — submit now
    submitted: bool                             # Form was successfully emailed

    # Output
    response_text: str                          # What ARIA says next → sent to TTS
    display_data: Optional[dict]                # Extra data for frontend UI panels
    response_chunks: Optional[list]             # Optional streaming-style chunks

    # Error
    error: Optional[str]
