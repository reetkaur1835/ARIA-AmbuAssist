import sqlite3
import os

# ── Single database for everything ────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'aria.db')


def get_db() -> sqlite3.Connection:
    """Single connection to aria.db — all tables live here."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Keep these aliases so existing imports don't break during transition
def get_aria_db() -> sqlite3.Connection:
    return get_db()

def get_shifts_db() -> sqlite3.Connection:
    return get_db()


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        -- ── PARAMEDICS ─────────────────────────────────────────────────────
        -- username is the single medic identifier (e.g. "Team01")
        -- used as PK and FK everywhere
        CREATE TABLE IF NOT EXISTS paramedics (
            username    TEXT PRIMARY KEY NOT NULL,   -- e.g. "Team01"
            first_name  TEXT NOT NULL,
            last_name   TEXT NOT NULL,
            badge_number TEXT NOT NULL,
            email       TEXT NOT NULL,
            station     TEXT,
            role        TEXT DEFAULT 'PCP',
            is_acp      INTEGER DEFAULT 0,
            phone       TEXT,
            pin         TEXT DEFAULT '1234',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ── SHIFTS ─────────────────────────────────────────────────────────
        -- medic_1 / medic_2 reference paramedics.username
        CREATE TABLE IF NOT EXISTS shifts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            station     TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            unit_id     TEXT,
            medic_1     TEXT REFERENCES paramedics(username),
            medic_2     TEXT REFERENCES paramedics(username)
        );

        -- ── FORM SUBMISSIONS ───────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS form_submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            form_type    TEXT NOT NULL,
            submitted_by TEXT NOT NULL REFERENCES paramedics(username),
            form_data    TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            emailed_to   TEXT,
            email_status TEXT DEFAULT 'pending'
        );

        -- ── PARAMEDIC STATUS / CHECKLIST ───────────────────────────────────
        CREATE TABLE IF NOT EXISTS paramedic_status (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL REFERENCES paramedics(username),
            item_code   TEXT NOT NULL,
            item_type   TEXT NOT NULL,
            description TEXT,
            status      TEXT DEFAULT 'GOOD',
            issue_count INTEGER DEFAULT 0,
            notes       TEXT,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, item_code)
        );
    """)

    # ── SEED PARAMEDICS (username = Team0X) ───────────────────────────────────
    cursor.executemany("""
        INSERT OR IGNORE INTO paramedics
        (username, first_name, last_name, badge_number, email, station, role, pin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        ("Team01", "James",  "Carter", "B-304", "jcarter@ems.ca", "Main St.",  "PCP", "1234"),
        ("Team02", "Sarah",  "Nguyen", "B-412", "snguyen@ems.ca", "Woodgrove", "ACP", "1234"),
        ("Team03", "Mike",   "Torres", "B-218", "mtorres@ems.ca", "Bedford",   "PCP", "1234"),
        ("Team04", "Priya",  "Patel",  "B-501", "ppatel@ems.ca",  "Coral",     "PCP", "1234"),
        ("Team09", "Leon",   "Brooks", "B-610", "lbrooks@ems.ca", "Main St.",  "PCP", "1234"),
        ("Team10", "Aisha",  "Khan",   "B-711", "akhan@ems.ca",   "Main St.",  "PCP", "1234"),
        ("Team21", "Carlos", "Rivera", "B-820", "crivera@ems.ca", "Coral",     "PCP", "1234"),
        ("Team22", "Nina",   "Scott",  "B-921", "nscott@ems.ca",  "Coral",     "ACP", "1234"),
        ("Team25", "Omar",   "Hassan", "B-105", "ohassan@ems.ca", "Main St.",  "PCP", "1234"),
        ("Team26", "Mei",    "Lin",    "B-206", "mlin@ems.ca",    "Main St.",  "PCP", "1234"),
        ("Team43", "Dana",   "White",  "B-430", "dwhite@ems.ca",  "Bedford",   "PCP", "1234"),
        ("Team44", "Raj",    "Patel",  "B-531", "rpatel@ems.ca",  "Bedford",   "ACP", "1234"),
    ])

    # ── SEED SHIFTS ───────────────────────────────────────────────────────────
    cursor.executemany("""
        INSERT OR IGNORE INTO shifts (date, station, start_time, end_time, unit_id, medic_1, medic_2)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        ('2026-03-01', 'Main St.',  '07:00', '19:00', '1122', 'Team01', 'Team02'),
        ('2026-03-01', 'Main St.',  '19:00', '07:00', '1122', 'Team03', 'Team04'),
        ('2026-03-01', 'Woodgrove', '07:00', '19:00', '3344', 'Team09', 'Team10'),
        ('2026-03-02', 'Main St.',  '07:00', '19:00', '1122', 'Team25', 'Team26'),
        ('2026-03-02', 'Bedford',   '19:00', '07:00', '6677', 'Team43', 'Team44'),
        ('2026-03-02', 'Coral',     '07:00', '19:00', '8899', 'Team21', 'Team22'),
        ('2026-03-04', 'Main St.',  '07:00', '19:00', '1122', 'Team01', 'Team02'),
        ('2026-03-05', 'Woodgrove', '07:00', '19:00', '3344', 'Team01', 'Team09'),
        ('2026-03-06', 'Bedford',   '19:00', '07:00', '6677', 'Team03', 'Team04'),
        ('2026-03-07', 'Coral',     '07:00', '19:00', '8899', 'Team21', 'Team22'),
        ('2026-03-08', 'Main St.',  '07:00', '19:00', '1122', 'Team25', 'Team26'),
    ])

    # ── SEED STATUS ITEMS ─────────────────────────────────────────────────────
    status_items = [
        ("ACRc",    "ACR Completion",  "Unfinished ACRs/PCRs",                    "BAD",  2, "Complete within 24h of call"),
        ("ACEr",    "ACE Response",    "ACE reviews requiring comment",           "GOOD", 0, "Complete within 1 week of BH review"),
        ("CERT-DL", "Drivers License", "Drivers License Validity",                "GOOD", 0, "Drivers License Status"),
        ("CERT-Va", "Vaccinations",    "Required vaccinations up to date",        "BAD",  1, "Vaccination Status as per guidelines"),
        ("CERT-CE", "Education",       "Continuous Education Status",             "GOOD", 0, "CME outstanding"),
        ("UNIF",    "Uniform",         "Uniform credits",                         "GOOD", 5, "Available Uniform order Credits"),
        ("CRIM",    "CRC",             "Criminal Record Check",                   "GOOD", 0, "Criminal Issue Free"),
        ("ACP",     "ACP Status",      "If ACP, Cert Valid",                      "GOOD", 0, "ACP Status is good if ACP"),
        ("VAC",     "Vacation",        "Vacation Requested and approved",         "GOOD", 0, "Yearly vacation approved"),
        ("MEALS",   "Missed Meals",    "Missed Meal Claims",                      "GOOD", 0, "Missed Meal Claims outstanding"),
        ("OVER",    "Overtime Req.",   "Overtime Requests outstanding",           "BAD",  1, "Overtime claims outstanding"),
    ]

    all_usernames = [
        "Team01","Team02","Team03","Team04","Team09","Team10",
        "Team21","Team22","Team25","Team26","Team43","Team44",
    ]

    for username in all_usernames:
        for item in status_items:
            cursor.execute("""
                INSERT OR IGNORE INTO paramedic_status
                (username, item_code, item_type, description, status, issue_count, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (username, *item))

    conn.commit()
    conn.close()
    print("✅ aria.db initialized at:", os.path.abspath(DB_PATH))


if __name__ == "__main__":
    init_db()
