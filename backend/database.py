import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "eventsphere.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str = "eventsphere_secure_salt_2025") -> str:
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def init_db():
    conn = get_db()
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
            budget                REAL    NOT NULL DEFAULT 0,
            status                TEXT    DEFAULT 'planned',       -- 'planned', 'published', 'completed', 'cancelled', 'draft'
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

    # ── 10. Safe Column Migrations for Existing Databases ─────────────────────
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
        ("events", "created_at", "TEXT DEFAULT (datetime('now'))"),
        ("events", "updated_at", "TEXT DEFAULT (datetime('now'))"),
        ("attendees", "user_id", "INTEGER"),
        ("attendees", "custom_fields", "TEXT DEFAULT '{}'"),
        ("attendees", "checkin_time", "TEXT DEFAULT NULL"),
        ("attendees", "cancelled_at", "TEXT DEFAULT NULL"),
        ("tickets", "qr_token", "TEXT DEFAULT ''"),
        ("tickets", "issued_at", "TEXT DEFAULT (datetime('now'))"),
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

    # ── 11. Seed Default Users & Initial Data ─────────────────────────────────
    seed_users = [
        ("System Administrator", "admin@eventsphere.com", "admin123", "admin", "Infosys ERP Admin"),
        ("Event Organizer", "organizer@eventsphere.com", "organizer123", "organizer", "Tech Events Council"),
        ("Arun Kumar", "user@eventsphere.com", "user123", "participant", "Anna University"),
        ("Sneha Sharma", "sneha@eventsphere.com", "user123", "participant", "IIT Madras"),
    ]

    for name, email, pwd, role, org in seed_users:
        existing = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not existing:
            cur.execute(
                """INSERT INTO users (name, email, password_hash, role, organization)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, email, hash_password(pwd), role, org),
            )

    conn.commit()
    conn.close()
