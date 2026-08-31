from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db
from auth import get_current_user, get_optional_current_user, require_roles
from ops import (
    CREATABLE_STATUSES,
    LOCKED_STATUSES,
    assert_transition,
    find_venue_conflict,
    maybe_auto_advance,
    normalize_status,
    occupancy_count,
    remaining_seats,
    write_audit,
    notify,
)

router = APIRouter()


class EventIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    event_type: str
    date: str
    time: str
    end_time: Optional[str] = ""
    budget: float = Field(0.0, ge=0.0)
    status: Optional[str] = "draft"
    venue_id: Optional[int] = None
    description: Optional[str] = ""
    banner_url: Optional[str] = ""
    capacity: int = Field(100, ge=1, le=100000)
    registration_deadline: Optional[str] = ""
    is_online: Optional[bool] = False
    meeting_link: Optional[str] = ""
    category: Optional[str] = "Technology"
    visibility: Optional[str] = "public"


class AssignVenueIn(BaseModel):
    venue_id: int


class StatusIn(BaseModel):
    status: str


def _decorate_event(db, row) -> dict:
    d = dict(row)
    d = maybe_auto_advance(db, d)
    d["capacity"] = d.get("capacity") or 100
    d["registered_count"] = d.get("registered_count")
    if d["registered_count"] is None:
        d["registered_count"] = occupancy_count(db, d["id"])
    d["remaining_seats"] = remaining_seats(db, d["id"], d["capacity"])
    d["is_full"] = d["remaining_seats"] <= 0
    return d


def _assert_event_access(event, current_user, write=False):
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user and current_user["role"] == "admin":
        return
    if write:
        if not current_user or event["organizer_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You do not have permission to modify this event.")


def _assert_venue_available(db, venue_id, candidate, exclude_event_id=None):
    if not venue_id or candidate.get("is_online"):
        return
    venue = db.execute("SELECT * FROM venues WHERE id = ?", (venue_id,)).fetchone()
    if not venue:
        raise HTTPException(status_code=404, detail="Selected venue not found.")
    if not venue["availability"]:
        raise HTTPException(status_code=400, detail="Selected venue is currently marked unavailable.")
    conflict = find_venue_conflict(db, venue_id, candidate, exclude_event_id)
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Venue overlap: '{conflict['name']}' already uses this hall on {conflict['date']} "
                f"({conflict['time']}–{conflict.get('end_time') or 'end'})."
            ),
        )


def _cancel_event_side_effects(db, event, current_user):
    attendees = db.execute(
        "SELECT id, user_id, email, name, status FROM attendees WHERE event_id = ? AND status != 'cancelled'",
        (event["id"],),
    ).fetchall()
    now_str = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for att in attendees:
        db.execute(
            "UPDATE attendees SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
            (now_str, att["id"]),
        )
        db.execute("UPDATE tickets SET status = 'cancelled' WHERE attendee_id = ?", (att["id"],))
        notify(
            db,
            att["user_id"],
            att["email"],
            event["id"],
            "🚫 Event Cancelled",
            f"'{event['name']}' has been cancelled. Your registration is no longer active.",
            "cancellation",
        )

    vendors = db.execute(
        """SELECT v.id, v.name, v.email, v.contact
           FROM vendor_assignments va
           JOIN vendors v ON v.id = va.vendor_id
           WHERE va.event_id = ?""",
        (event["id"],),
    ).fetchall()
    for vendor in vendors:
        notify(
            db,
            None,
            vendor["email"] or "",
            event["id"],
            "🚫 Event Cancelled — Vendor Notice",
            f"Assignment for '{event['name']}' is cancelled. Vendor: {vendor['name']}.",
            "cancellation",
        )

    write_audit(
        db,
        current_user,
        "event.cancel",
        "event",
        event["id"],
        event["name"],
        event["status"],
        "cancelled",
    )


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_event(
    event: EventIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()

    initial_status = normalize_status(event.status or "draft")
    if initial_status not in CREATABLE_STATUSES:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Events can only be initially created in 'draft' or 'published' status, not '{initial_status.upper()}'.",
        )

    # Validate venue availability and time-window conflicts
    _assert_venue_available(db, event.venue_id, event.model_dump())

    cur = db.execute(
        """INSERT INTO events (
               name, event_type, date, time, end_time, budget, status, venue_id,
               description, banner_url, capacity, registration_deadline,
               is_online, meeting_link, category, visibility, organizer_id
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.name.strip(),
            event.event_type,
            event.date,
            event.time,
            event.end_time or "",
            event.budget,
            initial_status,
            event.venue_id,
            event.description,
            event.banner_url,
            event.capacity,
            event.registration_deadline,
            1 if event.is_online else 0,
            event.meeting_link,
            event.category,
            event.visibility or "public",
            current_user["id"],
        ),
    )
    eid = cur.lastrowid

    write_audit(
        db,
        actor=current_user,
        action="event.create",
        object_type="event",
        object_id=eid,
        object_label=event.name.strip(),
        new_value={"name": event.name.strip(), "status": initial_status, "date": event.date, "time": event.time},
    )

    db.commit()
    db.close()

    return {"id": eid, "message": f"Event created successfully in '{initial_status}' status.", **event.model_dump(), "status": initial_status, "organizer_id": current_user["id"]}


@router.get("")
@router.get("/")
def get_events(
    search: Optional[str] = None,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    is_online: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    visibility: Optional[str] = None,
    sort_by: Optional[str] = "date",
    order: Optional[str] = "asc",
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    db = get_db()
    query = """
        SELECT e.*, v.name AS venue_name, v.location AS venue_location,
               u.name AS organizer_name, u.organization AS organizer_org,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'registered') AS registered_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'waitlisted') AS waitlisted_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'attended') AS attended_count
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.id
        LEFT JOIN users u ON e.organizer_id = u.id
        WHERE 1=1
    """
    params = []

    # Non-admin users see public events by default or their own
    if not current_user or current_user["role"] not in ["admin"]:
        if current_user and current_user["role"] == "organizer":
            query += " AND (e.visibility = 'public' OR e.organizer_id = ?)"
            params.append(current_user["id"])
        else:
            query += " AND e.visibility = 'public'"

    if search:
        query += " AND (e.name LIKE ? OR e.description LIKE ? OR e.category LIKE ? OR v.name LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if category and category != "All":
        query += " AND e.category = ?"
        params.append(category)

    if event_type and event_type != "All":
        query += " AND e.event_type = ?"
        params.append(event_type)

    if status_filter and status_filter != "All":
        query += " AND e.status = ?"
        params.append(status_filter)

    if is_online is not None:
        query += " AND e.is_online = ?"
        params.append(1 if is_online else 0)

    if date_from:
        query += " AND e.date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND e.date <= ?"
        params.append(date_to)

    valid_sorts = {"date": "e.date", "name": "e.name", "capacity": "e.capacity", "created_at": "e.created_at"}
    sort_column = valid_sorts.get(sort_by, "e.date")
    sort_order = "DESC" if order and order.lower() == "desc" else "ASC"

    query += f" ORDER BY {sort_column} {sort_order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    db.close()

    result = []
    for r in rows:
        d = dict(r)
        d["capacity"] = d["capacity"] or 100
        d["remaining_seats"] = max(0, d["capacity"] - (d["registered_count"] or 0))
        d["is_full"] = d["remaining_seats"] <= 0
        result.append(d)

    return result


@router.get("/organizer/my-events")
def get_my_events(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    query = """
        SELECT e.*, v.name AS venue_name, v.location AS venue_location,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'registered') AS registered_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'waitlisted') AS waitlisted_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'attended') AS attended_count
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.id
    """
    params = []
    if current_user["role"] != "admin":
        query += " WHERE e.organizer_id = ?"
        params.append(current_user["id"])

    query += " ORDER BY e.date DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    result = []
    for r in rows:
        d = dict(r)
        d["remaining_seats"] = max(0, (d["capacity"] or 100) - (d["registered_count"] or 0))
        result.append(d)
    return result


@router.get("/{event_id}")
def get_event(event_id: int):
    db = get_db()
    row = db.execute("""
        SELECT e.*, v.name AS venue_name, v.location AS venue_location, v.capacity AS venue_capacity,
               u.name AS organizer_name, u.organization AS organizer_org, u.email AS organizer_email,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'registered') AS registered_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'waitlisted') AS waitlisted_count,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'attended') AS attended_count
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.id
        LEFT JOIN users u ON e.organizer_id = u.id
        WHERE e.id = ?
    """, (event_id,)).fetchone()
    db.close()

    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    d = dict(row)
    d["capacity"] = d["capacity"] or 100
    d["remaining_seats"] = max(0, d["capacity"] - (d["registered_count"] or 0))
    d["is_full"] = d["remaining_seats"] <= 0
    return d


@router.put("/{event_id}")
def update_event(
    event_id: int,
    event: EventIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Scoped permissions: organizer can only edit own events
    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to edit this event.")

    current_status = normalize_status(row["status"])
    target_status = normalize_status(event.status or current_status)

    # 1. Lifecycle Immutability Check: Locked events cannot have details edited
    if current_status in LOCKED_STATUSES:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit event in '{current_status.upper()}' status. Historical or cancelled events are locked.",
        )

    # 2. Lifecycle Transition Validation
    if target_status != current_status:
        try:
            assert_transition(current_status, target_status)
        except HTTPException:
            db.close()
            raise

    # 3. Venue validation with time-window overlap conflict detection
    if event.venue_id:
        try:
            _assert_venue_available(db, event.venue_id, event.model_dump(), exclude_event_id=event_id)
        except HTTPException:
            db.close()
            raise

    # 4. If status is being transitioned to CANCELLED, execute cancellation side-effects
    if target_status == "cancelled" and current_status != "cancelled":
        _cancel_event_side_effects(db, dict(row), current_user)

    db.execute(
        """UPDATE events SET
               name=?, event_type=?, date=?, time=?, end_time=?, budget=?, status=?,
               venue_id=?, description=?, banner_url=?, capacity=?,
               registration_deadline=?, is_online=?, meeting_link=?,
               category=?, visibility=?
           WHERE id=?""",
        (

            event.name.strip(),
            event.event_type,
            event.date,
            event.time,
            event.end_time or "",
            event.budget,
            target_status,
            event.venue_id,
            event.description,
            event.banner_url,
            event.capacity,
            event.registration_deadline,
            1 if event.is_online else 0,
            event.meeting_link,
            event.category,
            event.visibility,
            event_id,
        ),
    )

    action_name = "event.status_change" if target_status != current_status else "event.update"
    write_audit(
        db,
        actor=current_user,
        action=action_name,
        object_type="event",
        object_id=event_id,
        object_label=event.name.strip(),
        previous_value={"status": current_status, "date": row["date"], "venue_id": row["venue_id"]},
        new_value={"status": target_status, "date": event.date, "venue_id": event.venue_id},
    )

    db.commit()
    db.close()
    return {"id": event_id, "message": "Event updated successfully", **event.model_dump(), "status": target_status}


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute("SELECT id, name, status, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to delete this event.")

    write_audit(
        db,
        actor=current_user,
        action="event.delete",
        object_type="event",
        object_id=event_id,
        object_label=row["name"],
        previous_value={"status": row["status"]},
        new_value=None,
    )

    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    db.close()
    return {"message": "Event deleted successfully"}


@router.put("/{event_id}/venue")
def assign_venue(
    event_id: int,
    body: AssignVenueIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to modify this event.")

    if event["status"] in LOCKED_STATUSES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Cannot assign venue to a {event['status']} event.")

    _assert_venue_available(db, body.venue_id, dict(event), exclude_event_id=event_id)

    db.execute("UPDATE events SET venue_id = ?, updated_at = datetime('now') WHERE id = ?", (body.venue_id, event_id))
    write_audit(
        db,
        actor=current_user,
        action="event.assign_venue",
        object_type="event",
        object_id=event_id,
        object_label=event["name"],
        previous_value={"venue_id": event["venue_id"]},
        new_value={"venue_id": body.venue_id},
    )
    db.commit()
    db.close()
    return {"message": "Venue assigned successfully"}
