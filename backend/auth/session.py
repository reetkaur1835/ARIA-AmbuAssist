import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.setup import get_db

# In-memory session store
active_sessions: dict[str, dict] = {}


def authenticate_paramedic(username: str, pin: str) -> dict | None:
    """Returns paramedic dict if credentials valid, None if not."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM paramedics WHERE username = ? AND pin = ?",
        (username.strip(), pin.strip())
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(paramedic: dict) -> str:
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = paramedic
    return session_id


def get_current_paramedic(session_id: str) -> dict | None:
    return active_sessions.get(session_id)


def end_session(session_id: str):
    active_sessions.pop(session_id, None)


def lookup_paramedic_by_number(username: str) -> dict | None:
    """Look up a paramedic by username (e.g. 'Team01')."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM paramedics WHERE username = ?",
        (username.strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
