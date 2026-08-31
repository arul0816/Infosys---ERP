import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "eventsphere.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def hash_password(password: str, salt: str = "eventsphere_secure_salt_2025") -> str:
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def init_db():
    conn = get_db()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except Exception:
        pass
    cur = conn.cursor()


    # ── 1. Users Table ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'participant', -- 'admin', 'organizer', 'participant'
            avatar_url    TEXT    DEFAULT '',
            phone         TEXT    DEFAULT '',
            organization  TEXT    DEFAULT '',
            status        TEXT    DEFAULT 'active',              -- 'active', 'inactive', 'suspended'
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 2. Venues Table ───────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS venues (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            capacity     INTEGER NOT NULL,
            location     TEXT    NOT NULL,
            availability INTEGER DEFAULT 1
        )
    """)

    # ── 3. Resources Table ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            quantity INTEGER NOT NULL,
            status   TEXT    DEFAULT 'available'
        )
    """)

    # ── 4. Events Table ───────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            name                  TEXT    NOT NULL,
            event_type            TEXT    NOT NULL,
            date                  TEXT    NOT NULL,
            time                  TEXT    NOT NULL,
            end_time              TEXT    DEFAULT '',
            budget                REAL    NOT NULL DEFAULT 0,
            status                TEXT    DEFAULT 'draft',         -- 'draft', 'published', 'ongoing', 'completed', 'cancelled'
            venue_id              INTEGER,
            description           TEXT    DEFAULT '',
            banner_url            TEXT    DEFAULT '',
            capacity              INTEGER DEFAULT 100,
            registration_deadline TEXT    DEFAULT '',
            is_online             INTEGER DEFAULT 0,
            meeting_link          TEXT    DEFAULT '',
            category              TEXT    DEFAULT 'Technology',
            visibility            TEXT    DEFAULT 'public',        -- 'public', 'private'
            organizer_id          INTEGER,
            created_at            TEXT    DEFAULT (datetime('now')),
            updated_at            TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (venue_id)     REFERENCES venues(id) ON DELETE SET NULL,
            FOREIGN KEY (organizer_id) REFERENCES users(id)  ON DELETE SET NULL
        )
    """)

    # ── 5. Event Resources Allocation ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_resources (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id      INTEGER NOT NULL,
            resource_id   INTEGER NOT NULL,
            quantity_used INTEGER NOT NULL,
            FOREIGN KEY (event_id)    REFERENCES events(id)    ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )
    """)

    # ── 6. Attendees Table ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendees (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id      INTEGER NOT NULL,
            user_id       INTEGER,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL,
            phone         TEXT    NOT NULL,
            college       TEXT    DEFAULT '',
            status        TEXT    DEFAULT 'registered', -- 'registered', 'waitlisted', 'attended', 'absent', 'cancelled'
            custom_fields TEXT    DEFAULT '{}',
            checkin_time  TEXT    DEFAULT NULL,
            cancelled_at  TEXT    DEFAULT NULL,
            registered_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE SET NULL
        )
    """)

    # ── 7. Tickets Table ──────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            attendee_id INTEGER NOT NULL UNIQUE,
            event_id    INTEGER NOT NULL,
            ticket_id   TEXT    NOT NULL UNIQUE,
            qr_token    TEXT    DEFAULT '',
            status      TEXT    DEFAULT 'active', -- 'active', 'used', 'cancelled'
            issued_at   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (attendee_id) REFERENCES attendees(id) ON DELETE CASCADE,
            FOREIGN KEY (event_id)    REFERENCES events(id)    ON DELETE CASCADE
        )
    """)

    # ── 8. Vendors & Assignments ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            service_type TEXT    NOT NULL,
            contact      TEXT    NOT NULL,
            email        TEXT    DEFAULT '',
            rating       REAL    DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendor_assignments (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            event_id  INTEGER NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)  ON DELETE CASCADE,
            FOREIGN KEY (event_id)  REFERENCES events(id)   ON DELETE CASCADE
        )
    """)

    # ── 9. Notifications Table ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            email      TEXT    DEFAULT '',
            event_id   INTEGER,
            title      TEXT    NOT NULL,
            message    TEXT    NOT NULL,
            type       TEXT    NOT NULL DEFAULT 'info', -- 'registration', 'waitlist_promoted', 'reminder', 'cancellation', 'checkin'
            is_read    INTEGER DEFAULT 0,
            created_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL
        )
    """)

    # ── 10. Budget Management Table ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        INTEGER NOT NULL UNIQUE,
            total_budget    REAL    NOT NULL DEFAULT 0,
            notes           TEXT    DEFAULT '',
            created_by      INTEGER NOT NULL,
            created_at      TEXT    DEFAULT (datetime('now')),
            updated_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id)   REFERENCES events(id)  ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id)   ON DELETE SET NULL
        )
    """)

    # ── 11. Expense Tracking Table ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    INTEGER NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'Other', -- 'Venue', 'Catering', 'Marketing', 'Equipment', 'Staffing', 'Transportation', 'Logistics', 'Other'
            description TEXT    NOT NULL,
            amount      REAL    NOT NULL DEFAULT 0,
            date        TEXT    NOT NULL,
            vendor_id   INTEGER,
            status      TEXT    DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
            created_by  INTEGER NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id)   REFERENCES events(id)     ON DELETE CASCADE,
            FOREIGN KEY (vendor_id)  REFERENCES vendors(id)    ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users(id)      ON DELETE SET NULL
        )
    """)

    # ── 12. Sponsorship Management Table ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sponsors (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id            INTEGER NOT NULL,
            sponsor_name        TEXT    NOT NULL,
            contact_person      TEXT    DEFAULT '',
            contact_email       TEXT    DEFAULT '',
            contact_phone       TEXT    DEFAULT '',
            sponsorship_amount  REAL    NOT NULL DEFAULT 0,
            sponsorship_type    TEXT    DEFAULT 'Gold', -- 'Platinum', 'Gold', 'Silver', 'Bronze', 'In-kind'
            status              TEXT    DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'confirmed'
            notes               TEXT    DEFAULT '',
            created_by          INTEGER NOT NULL,
            created_at          TEXT    DEFAULT (datetime('now')),
            updated_at          TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id)   REFERENCES events(id)  ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id)   ON DELETE SET NULL
        )
    """)

    # ── 13. Approval Workflow Table ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        INTEGER NOT NULL,
            requester_id    INTEGER NOT NULL,
            request_type    TEXT    NOT NULL, -- 'vendor', 'expense', 'resource', 'sponsorship'
            reference_id    INTEGER NOT NULL,
            amount          REAL    DEFAULT 0,
            reason          TEXT    DEFAULT '',
            status          TEXT    DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
            reviewed_by     INTEGER,
            reviewed_at     TEXT    DEFAULT NULL,
            reviewer_comment TEXT   DEFAULT '',
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id)    REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewed_by) REFERENCES users(id)  ON DELETE SET NULL
        )
    """)

    # ── 14. Reminder Tracking Table ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminder_tracking (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        INTEGER NOT NULL,
            user_id         INTEGER,
            email           TEXT    DEFAULT '',
            reminder_type   TEXT    NOT NULL, -- '24h', '1h'
            scheduled_time  TEXT    NOT NULL,
            sent_at         TEXT    DEFAULT NULL,
            is_sent         INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE
        )
    """)

    # ── 15. Vendor Performance Ratings Table ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendor_performance (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id           INTEGER NOT NULL,
            event_id            INTEGER NOT NULL,
            quality_rating      INTEGER DEFAULT 3, -- 1-5
            timeliness_rating   INTEGER DEFAULT 3, -- 1-5
            cost_rating         INTEGER DEFAULT 3, -- 1-5
            communication_rating INTEGER DEFAULT 3, -- 1-5
            overall_rating      INTEGER DEFAULT 3, -- 1-5
            comments            TEXT    DEFAULT '',
            rated_by            INTEGER NOT NULL,
            created_at          TEXT    DEFAULT (datetime('now')),
            updated_at          TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (vendor_id)  REFERENCES vendors(id)  ON DELETE CASCADE,
            FOREIGN KEY (event_id)   REFERENCES events(id)   ON DELETE CASCADE,
            FOREIGN KEY (rated_by)   REFERENCES users(id)    ON DELETE SET NULL
        )
    """)

    # ── 16. Audit Logs ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id       INTEGER,
            actor_name     TEXT    DEFAULT 'System',
            actor_role     TEXT    DEFAULT 'system',
            action         TEXT    NOT NULL,
            object_type    TEXT    NOT NULL,
            object_id      INTEGER,
            object_label   TEXT    DEFAULT '',
            previous_value TEXT    DEFAULT NULL,
            new_value      TEXT    DEFAULT NULL,
            created_at     TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # ── 17. Check-in Audit Trail ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id       INTEGER NOT NULL,
            attendee_id    INTEGER NOT NULL,
            ticket_id      TEXT    DEFAULT '',
            checked_in_by  INTEGER,
            checkin_time   TEXT    DEFAULT (datetime('now')),
            method         TEXT    DEFAULT 'qr',
            FOREIGN KEY (event_id)      REFERENCES events(id)    ON DELETE CASCADE,
            FOREIGN KEY (attendee_id)   REFERENCES attendees(id) ON DELETE CASCADE,
            FOREIGN KEY (checked_in_by) REFERENCES users(id)     ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_flags (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ── 18. Safe Column Migrations for Existing Databases ─────────────────────
    migrations = [
        ("events", "description", "TEXT DEFAULT ''"),
        ("events", "banner_url", "TEXT DEFAULT ''"),
        ("events", "capacity", "INTEGER DEFAULT 100"),
        ("events", "registration_deadline", "TEXT DEFAULT ''"),
        ("events", "is_online", "INTEGER DEFAULT 0"),
        ("events", "meeting_link", "TEXT DEFAULT ''"),
        ("events", "category", "TEXT DEFAULT 'Technology'"),
        ("events", "visibility", "TEXT DEFAULT 'public'"),
        ("events", "organizer_id", "INTEGER"),
        ("events", "created_at", "TEXT DEFAULT ''"),
        ("events", "updated_at", "TEXT DEFAULT ''"),
        ("events", "end_time", "TEXT DEFAULT ''"),
        ("attendees", "user_id", "INTEGER"),
        ("attendees", "custom_fields", "TEXT DEFAULT '{}'"),
        ("attendees", "checkin_time", "TEXT DEFAULT NULL"),
        ("attendees", "cancelled_at", "TEXT DEFAULT NULL"),
        ("tickets", "qr_token", "TEXT DEFAULT ''"),
        ("tickets", "issued_at", "TEXT DEFAULT ''"),
        ("users", "phone", "TEXT DEFAULT ''"),
        ("users", "organization", "TEXT DEFAULT ''"),
        ("users", "status", "TEXT DEFAULT 'active'"),
    ]

    for table, col, col_def in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            # Column already exists
            pass

    # Backfill timestamps for any blank records
    try:
        cur.execute("UPDATE events SET created_at = datetime('now') WHERE created_at = '' OR created_at IS NULL")
        cur.execute("UPDATE events SET updated_at = datetime('now') WHERE updated_at = '' OR updated_at IS NULL")
        cur.execute("UPDATE tickets SET issued_at = datetime('now') WHERE issued_at = '' OR issued_at IS NULL")
    except sqlite3.OperationalError:
        pass

    cur.execute("UPDATE events SET status = 'published' WHERE status = 'planned'")

    try:
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_active_attendee_email
               ON attendees(event_id, email) WHERE status != 'cancelled'"""
        )
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_active_attendee_user
               ON attendees(event_id, user_id)
               WHERE user_id IS NOT NULL AND status != 'cancelled'"""
        )
    except sqlite3.OperationalError:
        pass

    restored = cur.execute(
        "SELECT value FROM schema_flags WHERE key = 'resource_stock_restored'"
    ).fetchone()
    if not restored:
        cur.execute(
            """UPDATE resources SET quantity = quantity + COALESCE((
                   SELECT SUM(quantity_used) FROM event_resources er WHERE er.resource_id = resources.id
               ), 0)"""
        )
        cur.execute(
            "INSERT INTO schema_flags (key, value) VALUES ('resource_stock_restored', '1')"
        )

    # ── Demo admin account (development only) ─────────────────────────────────
    # Seed a single admin demo login; remove other legacy demo accounts.
    demo_admin_email = "admin@eventsphere.com"
    demo_admin_password = "admin123"
    legacy_demo_emails = (
        "organizer@eventsphere.com",
        "user@eventsphere.com",
        "sneha@eventsphere.com",
    )
    cur.execute(
        "DELETE FROM users WHERE email IN (?, ?, ?)",
        legacy_demo_emails,
    )
    admin_row = cur.execute(
        "SELECT id FROM users WHERE email = ?",
        (demo_admin_email,),
    ).fetchone()
    if not admin_row:
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, phone, organization, status)
               VALUES (?, ?, ?, 'admin', '', 'EventSphere', 'active')""",
            ("Demo Admin", demo_admin_email, hash_password(demo_admin_password)),
        )
    else:
        cur.execute(
            """UPDATE users SET password_hash = ?, role = 'admin', status = 'active', name = 'Demo Admin'
               WHERE email = ?""",
            (hash_password(demo_admin_password), demo_admin_email),
        )

    conn.commit()
    conn.close()

