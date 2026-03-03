"""
db_tools.py — All database query/update functions for ARIA agents.
Single DB: aria.db. Single medic identifier: username (e.g. "Team01").
"""
import json
from datetime import datetime, date
from database.setup import get_db


# ─────────────────────────────────────────────
# SHIFT QUERIES
# ─────────────────────────────────────────────

async def query_shifts(
    medic_identifier: str = None,
    station: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 10
) -> list[dict]:
    """Query shifts. medic_identifier matches medic_1 OR medic_2 (username)."""
    conn = get_db()
    query = "SELECT * FROM shifts WHERE 1=1"
    params = []

    if medic_identifier:
        query += " AND (medic_1 = ? OR medic_2 = ?)"
        params.extend([medic_identifier, medic_identifier])
    if station:
        query += " AND station = ?"
        params.append(station)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += f" ORDER BY date ASC, start_time ASC LIMIT {limit}"
    results = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in results]


async def get_upcoming_shifts(medic_identifier: str, days_ahead: int = 7) -> list[dict]:
    """Get next N days of shifts for a given username."""
    today = date.today().isoformat()
    return await query_shifts(
        medic_identifier=medic_identifier,
        date_from=today,
        limit=days_ahead * 2,
    )


# ─────────────────────────────────────────────
# PARAMEDIC STATUS / CHECKLIST
# ─────────────────────────────────────────────

def get_paramedic_status(username: str) -> list[dict]:
    """Fetch all status/checklist items for a paramedic, BAD items first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM paramedic_status WHERE username = ? ORDER BY status DESC",
        (username,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bad_status_items(username: str) -> list[dict]:
    """Return only BAD status items for a given paramedic."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM paramedic_status WHERE username = ? AND status = 'BAD'",
        (username,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_status_item(username: str, item_code: str) -> dict | None:
    """Fetch a single status item by username + item_code."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM paramedic_status WHERE username = ? AND item_code = ?",
        (username, item_code)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status_item(
    username: str,
    item_code: str,
    status: str,
    issue_count: int = 0,
    notes: str = None
):
    """Update a checklist item's status and issue_count."""
    conn = get_db()
    conn.execute("""
        UPDATE paramedic_status
        SET status = ?, issue_count = ?, notes = COALESCE(?, notes), updated_at = CURRENT_TIMESTAMP
        WHERE username = ? AND item_code = ?
    """, (status, issue_count, notes, username, item_code))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# FORM SUBMISSIONS
# ─────────────────────────────────────────────

def save_form_submission(
    form_type: str,
    submitted_by: str,
    form_data: dict,
    emailed_to: str = None,
    email_status: str = "pending"
) -> int:
    """Save a completed form to the DB. Returns the new row id."""
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO form_submissions (form_type, submitted_by, form_data, emailed_to, email_status)
        VALUES (?, ?, ?, ?, ?)
    """, (form_type, submitted_by, json.dumps(form_data), emailed_to, email_status))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def update_form_email_status(form_id: int, email_status: str, emailed_to: str = None):
    """Update email delivery status after SendGrid call."""
    conn = get_db()
    conn.execute("""
        UPDATE form_submissions
        SET email_status = ?, emailed_to = COALESCE(?, emailed_to)
        WHERE id = ?
    """, (email_status, emailed_to, form_id))
    conn.commit()
    conn.close()


def get_submissions_for_medic(username: str, limit: int = 20) -> list[dict]:
    """Return past form submissions for a paramedic."""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, form_type, submitted_at, emailed_to, email_status
        FROM form_submissions
        WHERE submitted_by = ?
        ORDER BY submitted_at DESC
        LIMIT ?
    """, (username, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
