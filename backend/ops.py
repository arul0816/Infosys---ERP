"""Shared operational rules: lifecycle, conflicts, occupancy, audit."""
import datetime
import json
import re
from typing import Optional

from fastapi import HTTPException

EVENT_STATUSES = ("draft", "published", "ongoing", "completed", "cancelled")
OCCUPYING_STATUSES = ("registered", "attended")
REGISTRABLE_STATUSES = ("published", "ongoing")
CHECKIN_STATUSES = ("published", "ongoing")
LOCKED_STATUSES = ("completed", "cancelled")

ALLOWED_TRANSITIONS = {
    "draft": {"published", "cancelled"},
    "published": {"ongoing", "cancelled", "completed"},
    "ongoing": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

CREATABLE_STATUSES = {"draft", "published"}


def normalize_status(status: Optional[str]) -> str:
    raw = (status or "published").strip().lower()
    if raw == "planned":
        return "published"
    if raw not in EVENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid event status '{status}'. Valid statuses: {', '.join(EVENT_STATUSES)}")
    return raw


def parse_time_minutes(value: Optional[str]) -> int:
    if not value:
        return 0
    text = str(value).strip().upper().replace(".", "")
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?$", text)
    if not match:
        return 0
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(4)
    if meridiem == "PM" and hour != 12:
        hour += 12
    if meridiem == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def event_window(event: dict) -> tuple[int, int]:
    start = parse_time_minutes(event.get("time"))
    end = parse_time_minutes(event.get("end_time"))
    if end <= start:
        end = start + 120  # Default 2-hour duration if end_time not specified
    return start, end


def windows_overlap(a: dict, b: dict) -> bool:
    if str(a.get("date") or "")[:10] != str(b.get("date") or "")[:10]:
        return False
    a_start, a_end = event_window(a)
    b_start, b_end = event_window(b)
    return a_start < b_end and b_start < a_end


def event_datetime_start(event: dict) -> Optional[datetime.datetime]:
    date_str = event.get("date")
    if not date_str:
        return None
    minutes = parse_time_minutes(event.get("time"))
    try:
        day = datetime.datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return day + datetime.timedelta(minutes=minutes)
    except ValueError:
        return None


def event_datetime_end(event: dict) -> Optional[datetime.datetime]:
    start = event_datetime_start(event)
    if not start:
        return None
    s, e = event_window(event)
    return start + datetime.timedelta(minutes=max(0, e - s))


def occupancy_count(db, event_id: int) -> int:
    return db.execute(
        "SELECT COUNT(*) FROM attendees WHERE event_id = ? AND status IN ('registered', 'attended')",
        (event_id,),
    ).fetchone()[0]


def remaining_seats(db, event_id: int, capacity: int) -> int:
    return max(0, (capacity or 100) - occupancy_count(db, event_id))


def registration_deadline_passed(deadline: Optional[str]) -> bool:
    if not deadline:
        return False
    clean = str(deadline).strip()
    if not clean:
        return False
    now = datetime.datetime.now()
    try:
        if "T" in clean:
            dt = datetime.datetime.fromisoformat(clean)
            return now > dt
        if " " in clean and len(clean) >= 16:
            dt = datetime.datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")
            return now > dt
    except Exception:
        pass
    today_str = now.strftime("%Y-%m-%d")
    return today_str > clean[:10]


def assert_transition(current: str, target: str):
    current = normalize_status(current)
    target = normalize_status(target)
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition event from '{current.upper()}' to '{target.upper()}'. Allowed target statuses from {current.upper()}: {', '.join(s.upper() for s in ALLOWED_TRANSITIONS.get(current, [])) or 'None'}.",
        )


def maybe_auto_advance(db, event: dict) -> dict:
    """Advance published→ongoing and ongoing→completed based on date/time."""
    if not event:
        return event
    status = normalize_status(event.get("status"))
    if status in LOCKED_STATUSES or status == "draft":
        return event
    now = datetime.datetime.now()
    start = event_datetime_start(event)
    end = event_datetime_end(event)
    new_status = status
    if status == "published" and start and now >= start:
        new_status = "ongoing"
    if status in ("published", "ongoing") and end and now >= end:
        new_status = "completed"
    if new_status != status:
        db.execute(
            "UPDATE events SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, event["id"]),
        )
        event = dict(event)
        event["status"] = new_status
        write_audit(
            db,
            actor={"id": None, "name": "System", "role": "system"},
            action="event.auto_advance",
            object_type="event",
            object_id=event["id"],
            object_label=event.get("name"),
            previous_value=status,
            new_value=new_status,
        )
    return event


def find_venue_conflict(db, venue_id: int, candidate: dict, exclude_event_id: Optional[int] = None):
    if not venue_id or candidate.get("is_online"):
        return None
    query = """
        SELECT id, name, date, time, end_time, status
        FROM events
        WHERE venue_id = ? AND status NOT IN ('cancelled', 'draft')
    """
    params = [venue_id]
    if exclude_event_id:
        query += " AND id != ?"
        params.append(exclude_event_id)
    for row in db.execute(query, params).fetchall():
        other = dict(row)
        if windows_overlap(candidate, other):
            return other
    return None


def find_resource_conflict(db, resource_id: int, event: dict, quantity_used: int, resource_qty: int, exclude_alloc_id: Optional[int] = None):
    query = """
        SELECT er.id, er.quantity_used, e.id AS event_id, e.name, e.date, e.time, e.end_time, e.status
        FROM event_resources er
        JOIN events e ON e.id = er.event_id
        WHERE er.resource_id = ? AND e.status NOT IN ('cancelled', 'draft')
    """
    params = [resource_id]
    if exclude_alloc_id:
        query += " AND er.id != ?"
        params.append(exclude_alloc_id)
    overlapping = 0
    conflict_event = None
    for row in db.execute(query, params).fetchall():
        other = dict(row)
        if windows_overlap(event, other):
            overlapping += other["quantity_used"] or 0
            conflict_event = other
    if overlapping + quantity_used > resource_qty:
        return conflict_event, overlapping
    return None, overlapping


def write_audit(
    db,
    actor: Optional[dict],
    action: str,
    object_type: str,
    object_id: Optional[int] = None,
    object_label: Optional[str] = None,
    previous_value=None,
    new_value=None,
):
    def stringify(value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    actor = actor or {}
    db.execute(
        """INSERT INTO audit_logs (
               actor_id, actor_name, actor_role, action, object_type, object_id,
               object_label, previous_value, new_value
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            actor.get("id"),
            actor.get("name") or "System",
            actor.get("role") or "system",
            action,
            object_type,
            object_id,
            object_label,
            stringify(previous_value),
            stringify(new_value),
        ),
    )


def notify(db, user_id, email, event_id, title, message, ntype="info"):
    db.execute(
        """INSERT INTO notifications (user_id, email, event_id, title, message, type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, email or "", event_id, title, message, ntype),
    )
