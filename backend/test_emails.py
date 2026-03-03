"""
test_emails.py — Standalone email send test for all three ARIA form types.
Run: python test_emails.py [occurrence|teddy|scr|all]
"""
import asyncio
import sys
import os

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from forms.renderer import (
    render_occurrence_report_html,
    render_teddy_bear_html,
    render_shift_change_html,
)
from forms.schemas import (
    OccurrenceReportSchema,
    TeddyBearSchema,
    ShiftChangeRequestSchema,
    OccurrenceType,
    GenderType,
    RecipientType,
    ShiftChangeAction,
)
from forms.email_sender import (
    send_occurrence_report,
    send_teddy_bear_form,
    send_shift_change_request,
)

TEST_EMAIL = os.getenv("SENDER_EMAIL", "")  # sends to yourself


# ─────────────────────────────────────────────
# OCCURRENCE REPORT
# ─────────────────────────────────────────────
async def test_occurrence():
    print("\n📋  Testing: Occurrence Report email...")
    data = OccurrenceReportSchema(
        date="2026-03-03",
        time="14:30",
        report_creator="Reet Kaur",
        badge_number="T002",
        creator_details="Badge T002, PCP",
        occurrence_type=OccurrenceType.vehicle,
        brief_description="Unit 4521 minor collision at Main & King",
        observation="No injuries. Unit sustained minor front-end damage. Dispatch notified.",
        vehicle_number="4521",
        requested_by="Dispatch",
        target_email=TEST_EMAIL,
        call_number="C-20260303-001",
        action_taken="Vehicle pulled from service pending inspection.",
    )
    html = render_occurrence_report_html(data)
    success = await send_occurrence_report(html, data.model_dump(), TEST_EMAIL)
    print(f"  {'✅ Sent' if success else '❌ Failed'} → {TEST_EMAIL}")
    return success


# ─────────────────────────────────────────────
# TEDDY BEAR
# ─────────────────────────────────────────────
async def test_teddy():
    print("\n🧸  Testing: Teddy Bear form email...")
    data = TeddyBearSchema(
        date_time="2026-03-03T14:30:00",
        primary_medic_first="Reet",
        primary_medic_last="Kaur",
        primary_medic_number="T002",
        recipient_age="7",
        recipient_gender=GenderType.female,
        recipient_type=RecipientType.patient,
        target_email=TEST_EMAIL,
    )
    html = render_teddy_bear_html(data)

    # Teddy bear also sends an XML attachment — generate a minimal one
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<TeddyBearRequest>
  <Date>{data.date_time}</Date>
  <Medic>{data.primary_medic_first} {data.primary_medic_last} ({data.primary_medic_number})</Medic>
  <RecipientAge>{data.recipient_age}</RecipientAge>
  <RecipientGender>{data.recipient_gender.value}</RecipientGender>
  <RecipientType>{data.recipient_type.value}</RecipientType>
</TeddyBearRequest>"""

    success = await send_teddy_bear_form(html, xml_content, data.model_dump(), TEST_EMAIL)
    print(f"  {'✅ Sent' if success else '❌ Failed'} → {TEST_EMAIL}")
    return success


# ─────────────────────────────────────────────
# SHIFT CHANGE REQUEST
# ─────────────────────────────────────────────
async def test_scr():
    print("\n🔄  Testing: Shift Change Request email...")
    data = ShiftChangeRequestSchema(
        first_name="Reet",
        last_name="Kaur",
        medic_number="T002",
        shift_date="2026-03-10",
        shift_start="07:00",
        shift_end="19:00",
        requested_action=ShiftChangeAction.swap,
        notes="Swapping with Team01 — pre-approved verbally.",
    )
    html = render_shift_change_html(data)
    success = await send_shift_change_request(html, data.model_dump())
    scr_email = os.getenv("SCR_EMAIL", "")
    print(f"  {'✅ Sent' if success else '❌ Failed'} → {scr_email}")
    return success


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if not TEST_EMAIL:
        print("❌  SENDER_EMAIL not set in .env — aborting.")
        sys.exit(1)

    results = {}
    if target in ("occurrence", "all"):
        results["occurrence"] = await test_occurrence()
    if target in ("teddy", "all"):
        results["teddy"] = await test_teddy()
    if target in ("scr", "all"):
        results["scr"] = await test_scr()

    print("\n──────────────────────────────────────")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'}  {name}")
    print("──────────────────────────────────────")
    if all(results.values()):
        print("All emails sent successfully.")
    else:
        print("Some emails failed — check output above.")


if __name__ == "__main__":
    asyncio.run(main())
