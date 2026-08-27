from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db
from auth import get_current_user, get_optional_current_user, require_roles

router = APIRouter()


class EventIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    event_type: str
    date: str
    time: str
    budget: float = Field(0.0, ge=0.0)
    status: Optional[str] = "published"
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


@router.post("/", status_code=201)
def create_event(
    event: EventIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()

    # Validate venue if assigned
    if event.venue_id:
        venue = db.execute("SELECT * FROM venues WHERE id = ?", (event.venue_id,)).fetchone()
        if not venue:
            db.close()
            raise HTTPException(status_code=404, detail="Selected venue not found.")
        if not venue["availability"]:
            db.close()
            raise HTTPException(status_code=400, detail="Selected venue is currently marked unavailable.")

        # Check date conflict
        conflict = db.execute(
            "SELECT id FROM events WHERE venue_id = ? AND date = ? AND status != 'cancelled'",
            (event.venue_id, event.date),
        ).fetchone()
        if conflict:
            db.close()
            raise HTTPException(status_code=400, detail="Venue is already booked for another event on this date.")

    cur = db.execute(
        """INSERT INTO events (
               name, event_type, date, time, budget, status, venue_id,
               description, banner_url, capacity, registration_deadline,
               is_online, meeting_link, category, visibility, organizer_id
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.name.strip(),
            event.event_type,
            event.date,
            event.time,
            event.budget,
            event.status or "published",
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
    db.commit()
    eid = cur.lastrowid
    db.close()

    return {"id": eid, "message": "Event created successfully", **event.model_dump(), "organizer_id": current_user["id"]}


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
    row = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Scoped permissions: organizer can only edit own events
    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to edit this event.")

    # Venue validation if changing venue
    if event.venue_id:
        venue = db.execute("SELECT * FROM venues WHERE id = ?", (event.venue_id,)).fetchone()
        if not venue:
            db.close()
            raise HTTPException(status_code=404, detail="Venue not found")
        conflict = db.execute(
            "SELECT id FROM events WHERE venue_id = ? AND date = ? AND id != ? AND status != 'cancelled'",
            (event.venue_id, event.date, event_id),
        ).fetchone()
        if conflict:
            db.close()
            raise HTTPException(status_code=400, detail="Venue already booked for another event on this date.")

    db.execute(
        """UPDATE events SET
               name=?, event_type=?, date=?, time=?, budget=?, status=?,
               venue_id=?, description=?, banner_url=?, capacity=?,
               registration_deadline=?, is_online=?, meeting_link=?,
               category=?, visibility=?, updated_at=datetime('now')
           WHERE id=?""",
        (
            event.name.strip(),
            event.event_type,
            event.date,
            event.time,
            event.budget,
            event.status,
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
    db.commit()
    db.close()
    return {"id": event_id, "message": "Event updated successfully", **event.model_dump()}


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to delete this event.")

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
    event = db.execute("SELECT id, date, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to modify this event.")

    venue = db.execute("SELECT * FROM venues WHERE id = ?", (body.venue_id,)).fetchone()
    if not venue:
        db.close()
        raise HTTPException(status_code=404, detail="Venue not found")

    if not venue["availability"]:
        db.close()
        raise HTTPException(status_code=400, detail="Venue is currently unavailable.")

    conflict = db.execute(
        """SELECT id FROM events
           WHERE venue_id = ? AND date = ? AND id != ? AND status != 'cancelled'""",
        (body.venue_id, event["date"], event_id),
    ).fetchone()
    if conflict:
        db.close()
        raise HTTPException(
            status_code=400,
            detail="Venue is already booked for another event on the same date",
        )

    db.execute("UPDATE events SET venue_id = ? WHERE id = ?", (body.venue_id, event_id))
    db.commit()
    db.close()
    return {"message": "Venue assigned successfully"}
