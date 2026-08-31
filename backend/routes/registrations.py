import json
import datetime
import threading
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db
from auth import (
    get_current_user,
    get_optional_current_user,
    require_roles,
    sign_ticket_payload,
    verify_ticket_payload,
)
from ops import (
    REGISTRABLE_STATUSES,
    CHECKIN_STATUSES,
    maybe_auto_advance,
    occupancy_count,
    registration_deadline_passed,
    write_audit,
    notify,
)

router = APIRouter()

REGISTRATION_LOCK = threading.Lock()


class RegistrationIn(BaseModel):
    event_id: int
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: str = Field(..., min_length=5)
    college: Optional[str] = ""
    custom_fields: Optional[dict] = {}


class CheckinVerifyIn(BaseModel):
    qr_data: Optional[str] = None
    ticket_id: Optional[str] = None
    attendee_id: Optional[int] = None
    event_id: Optional[int] = None


def auto_promote_waitlist(db, event_id: int):
    """Automatically promote the earliest waitlisted participant when a seat opens."""
    with REGISTRATION_LOCK:
        waitlisted = db.execute(
            """SELECT * FROM attendees
               WHERE event_id = ? AND status = 'waitlisted'
               ORDER BY registered_at ASC LIMIT 1""",
            (event_id,),
        ).fetchone()

        if waitlisted:
            aid = waitlisted["id"]
            # Promote attendee to registered
            db.execute("UPDATE attendees SET status = 'registered' WHERE id = ?", (aid,))

            # Issue ticket
            ticket_id = f"TKT{aid:04d}"
            qr_token = sign_ticket_payload(ticket_id, aid, event_id, waitlisted["email"])

            db.execute(
                """INSERT OR REPLACE INTO tickets (attendee_id, event_id, ticket_id, qr_token, status)
                   VALUES (?, ?, ?, ?, 'active')""",
                (aid, event_id, ticket_id, qr_token),
            )

            # Notify attendee
            event = db.execute("SELECT name FROM events WHERE id = ?", (event_id,)).fetchone()
            event_name = event["name"] if event else f"Event #{event_id}"
            notify(
                db,
                waitlisted["user_id"],
                waitlisted["email"],
                event_id,
                "🎉 You're in! Waitlist Promoted",
                f"A seat opened up for '{event_name}'! Your registration is now confirmed. Ticket ID: {ticket_id}.",
                "waitlist_promoted",
            )

            write_audit(
                db,
                actor={"id": None, "name": "System", "role": "system"},
                action="registration.waitlist_promoted",
                object_type="attendee",
                object_id=aid,
                object_label=waitlisted["name"],
                previous_value="waitlisted",
                new_value={"status": "registered", "ticket_id": ticket_id},
            )

            return {
                "promoted": True,
                "attendee_id": aid,
                "name": waitlisted["name"],
                "email": waitlisted["email"],
                "ticket_id": ticket_id,
                "qr_token": qr_token,
            }
        return {"promoted": False}


# ── Registration Endpoint ─────────────────────────────────────────────────────

@router.post("", status_code=201)
@router.post("/", status_code=201)
def register(
    reg: RegistrationIn,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    db = get_db()

    # 1. Check event exists and update auto-advancement
    event_row = db.execute(
        "SELECT * FROM events WHERE id = ?",
        (reg.event_id,),
    ).fetchone()
    if not event_row:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found.")

    event = maybe_auto_advance(db, dict(event_row))
    event_status = event["status"]

    # 2. Lifecycle Status Validation
    if event_status not in REGISTRABLE_STATUSES:
        db.close()
        if event_status == "draft":
            detail_msg = "Registration is not available. Event is currently an unannounced draft."
        elif event_status == "completed":
            detail_msg = "Registration is closed. Event has already concluded."
        elif event_status == "cancelled":
            detail_msg = "Registration is closed. Event has been cancelled."
        else:
            detail_msg = f"Registration is not available. Event status: '{event_status}'."
        raise HTTPException(status_code=400, detail=detail_msg)

    # 3. Check registration deadline
    if registration_deadline_passed(event.get("registration_deadline")):
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Registration deadline ({event['registration_deadline']}) has passed. Registration is now closed.",
        )

    # 4. Duplicate registration check — participant cannot register twice for same event
    # Check by email
    dup_email = db.execute(
        "SELECT id, status FROM attendees WHERE event_id = ? AND LOWER(email) = LOWER(?) AND status != 'cancelled'",
        (reg.event_id, reg.email.strip()),
    ).fetchone()
    if dup_email:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"This email address is already {dup_email['status']} for this event. A participant cannot register twice for the same event.",
        )

    # Check by user_id if authenticated
    user_id = current_user["id"] if current_user else None
    if user_id:
        dup_user = db.execute(
            "SELECT id, status FROM attendees WHERE event_id = ? AND user_id = ? AND status != 'cancelled'",
            (reg.event_id, user_id),
        ).fetchone()
        if dup_user:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Your account is already {dup_user['status']} for this event. A participant cannot register twice for the same event.",
            )

    custom_json = json.dumps(reg.custom_fields or {})
    capacity = event["capacity"] or 100

    # 5. Concurrency-Safe Atomic Capacity Management
    with REGISTRATION_LOCK:
        # Re-fetch registered count inside mutex
        occupied = occupancy_count(db, reg.event_id)

        if occupied < capacity:
            # Confirmed Registration
            status_val = "registered"
            cur = db.execute(
                """INSERT INTO attendees (event_id, user_id, name, email, phone, college, status, custom_fields)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (reg.event_id, user_id, reg.name.strip(), reg.email.lower().strip(), reg.phone.strip(), reg.college.strip(), status_val, custom_json),
            )
            attendee_id = cur.lastrowid

            # Generate ticket and signed QR
            ticket_id = f"TKT{attendee_id:04d}"
            qr_token = sign_ticket_payload(ticket_id, attendee_id, reg.event_id, reg.email)

            db.execute(
                """INSERT INTO tickets (attendee_id, event_id, ticket_id, qr_token, status)
                   VALUES (?, ?, ?, ?, 'active')""",
                (attendee_id, reg.event_id, ticket_id, qr_token),
            )

            # Create confirmation notification
            notify(
                db,
                user_id,
                reg.email.lower().strip(),
                reg.event_id,
                "✅ Registration Confirmed",
                f"You have registered successfully for '{event['name']}'. Your Ticket ID is {ticket_id}.",
                "registration",
            )

            write_audit(
                db,
                actor=current_user or {"id": user_id, "name": reg.name.strip(), "role": "participant"},
                action="registration.create_confirmed",
                object_type="attendee",
                object_id=attendee_id,
                object_label=reg.name.strip(),
                new_value={"event_id": reg.event_id, "ticket_id": ticket_id, "status": "registered"},
            )

            db.commit()
            db.close()

            return {
                "status": "registered",
                "attendee_id": attendee_id,
                "ticket_id": ticket_id,
                "qr_token": qr_token,
                "name": reg.name,
                "email": reg.email,
                "event_id": reg.event_id,
                "event_name": event["name"],
                "message": "Registration successful! Your digital ticket is ready.",
            }
        else:
            # Waitlist Placement
            status_val = "waitlisted"
            cur = db.execute(
                """INSERT INTO attendees (event_id, user_id, name, email, phone, college, status, custom_fields)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (reg.event_id, user_id, reg.name.strip(), reg.email.lower().strip(), reg.phone.strip(), reg.college.strip(), status_val, custom_json),
            )
            attendee_id = cur.lastrowid

            waitlist_pos = db.execute(
                "SELECT COUNT(*) FROM attendees WHERE event_id = ? AND status = 'waitlisted'",
                (reg.event_id,),
            ).fetchone()[0]

            notify(
                db,
                user_id,
                reg.email.lower().strip(),
                reg.event_id,
                "⏳ Added to Waitlist",
                f"'{event['name']}' is currently full. You are position #{waitlist_pos} on the waitlist. We will notify you if a seat opens.",
                "waitlist",
            )

            write_audit(
                db,
                actor=current_user or {"id": user_id, "name": reg.name.strip(), "role": "participant"},
                action="registration.create_waitlist",
                object_type="attendee",
                object_id=attendee_id,
                object_label=reg.name.strip(),
                new_value={"event_id": reg.event_id, "status": "waitlisted", "position": waitlist_pos},
            )

            db.commit()
            db.close()

            return {
                "status": "waitlisted",
                "attendee_id": attendee_id,
                "ticket_id": None,
                "qr_token": None,
                "name": reg.name,
                "email": reg.email,
                "event_id": reg.event_id,
                "event_name": event["name"],
                "waitlist_position": waitlist_pos,
                "message": f"Event capacity reached. You have been placed on the waitlist (Position #{waitlist_pos}).",
            }


# ── My Registrations (Authenticated User) ─────────────────────────────────────

@router.get("/my")
def get_my_registrations(current_user: dict = Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        """SELECT a.id, a.event_id, a.name, a.email, a.phone, a.college, a.status,
                  a.registered_at, a.checkin_time,
                  e.name AS event_name, e.date AS event_date, e.time AS event_time,
                  e.category AS event_category, e.is_online, e.meeting_link,
                  v.name AS venue_name, v.location AS venue_location,
                  t.ticket_id, t.qr_token, t.status AS ticket_status
           FROM attendees a
           JOIN events e ON a.event_id = e.id
           LEFT JOIN venues v ON e.venue_id = v.id
           LEFT JOIN tickets t ON t.attendee_id = a.id
           WHERE a.user_id = ? OR LOWER(a.email) = LOWER(?)
           ORDER BY a.registered_at DESC""",
        (current_user["id"], current_user["email"]),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── All Registrations (Organizer / Admin) ──────────────────────────────────────

@router.get("")
@router.get("/")
def get_all_registrations(
    event_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    query = """
        SELECT a.id, a.name, a.email, a.phone, a.college,
               a.status, a.registered_at, a.checkin_time, a.event_id,
               e.name AS event_name, e.organizer_id,
               t.ticket_id, t.qr_token, t.status AS ticket_status
        FROM attendees a
        JOIN events e ON a.event_id = e.id
        LEFT JOIN tickets t ON t.attendee_id = a.id
        WHERE 1=1
    """
    params = []

    # Scoped: organizer only sees registrations for own events
    if current_user["role"] != "admin":
        query += " AND e.organizer_id = ?"
        params.append(current_user["id"])

    if event_id:
        query += " AND a.event_id = ?"
        params.append(event_id)

    if status_filter and status_filter != "All":
        query += " AND a.status = ?"
        params.append(status_filter)

    if search:
        query += " AND (a.name LIKE ? OR a.email LIKE ? OR t.ticket_id LIKE ? OR a.phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY a.registered_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/event/{event_id}")
def get_registrations_by_event(event_id: int):
    db = get_db()
    rows = db.execute("""
        SELECT a.id, a.name, a.email, a.phone, a.college,
               a.status, a.registered_at, a.checkin_time,
               t.ticket_id, t.qr_token, t.status AS ticket_status
        FROM attendees a
        LEFT JOIN tickets t ON t.attendee_id = a.id
        WHERE a.event_id = ?
        ORDER BY a.registered_at
    """, (event_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/attendance/{event_id}")
def get_attendance(event_id: int):
    db = get_db()
    rows = db.execute("""
        SELECT a.id, a.name, a.email, a.phone, a.status, a.checkin_time, a.registered_at,
               t.ticket_id, t.qr_token
        FROM attendees a
        LEFT JOIN tickets t ON t.attendee_id = a.id
        WHERE a.event_id = ?
        ORDER BY a.name
    """, (event_id,)).fetchall()

    total      = len(rows)
    attended   = sum(1 for r in rows if r["status"] == "attended")
    absent     = sum(1 for r in rows if r["status"] == "absent")
    registered = sum(1 for r in rows if r["status"] == "registered")
    waitlisted = sum(1 for r in rows if r["status"] == "waitlisted")
    cancelled  = sum(1 for r in rows if r["status"] == "cancelled")
    db.close()

    return {
        "total": total,
        "attended": attended,
        "absent": absent,
        "registered": registered,
        "waitlisted": waitlisted,
        "cancelled": cancelled,
        "attendees": [dict(r) for r in rows],
    }


# ── Check-in & Verification ───────────────────────────────────────────────────

@router.post("/verify-checkin")
def verify_and_checkin(
    body: CheckinVerifyIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Validate QR cryptographic token or Ticket ID, enforce lifecycle & attendee status, and log check-in audit trail."""
    db = get_db()
    ticket_id = body.ticket_id
    attendee_id = body.attendee_id
    is_qr = bool(body.qr_data)

    # If QR data provided, parse and verify cryptographic signature
    if body.qr_data:
        qr_str = body.qr_data.strip()
        if qr_str.startswith("ESP:"):
            valid, t_data = verify_ticket_payload(qr_str)
            if not valid or not t_data:
                db.close()
                raise HTTPException(status_code=400, detail="Invalid or forged ticket QR cryptographic signature.")
            ticket_id = t_data["ticket_id"]
            attendee_id = t_data["attendee_id"]
        elif qr_str.startswith("EVENTSPHERE|"):
            # Legacy format support
            parts = qr_str.split("|")
            ticket_id = parts[1] if len(parts) > 1 else None
        else:
            ticket_id = qr_str

    if not ticket_id and not attendee_id:
        db.close()
        raise HTTPException(status_code=400, detail="Please provide a valid Ticket ID, Attendee ID, or QR payload.")

    # Find attendee, ticket, and event details
    if attendee_id:
        row = db.execute(
            """SELECT a.*, e.name AS event_name, e.status AS event_status, e.organizer_id,
                      t.ticket_id, t.status AS ticket_status
               FROM attendees a
               JOIN events e ON a.event_id = e.id
               LEFT JOIN tickets t ON t.attendee_id = a.id
               WHERE a.id = ?""",
            (attendee_id,),
        ).fetchone()
    else:
        row = db.execute(
            """SELECT a.*, e.name AS event_name, e.status AS event_status, e.organizer_id,
                      t.ticket_id, t.status AS ticket_status
               FROM tickets t
               JOIN attendees a ON t.attendee_id = a.id
               JOIN events e ON a.event_id = e.id
               WHERE t.ticket_id = ?""",
            (ticket_id,),
        ).fetchone()

    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Ticket or attendee registration record not found in system.")

    # Scoped authorization check: organizer can only check in attendees for own events
    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only check in attendees for your own assigned events.")

    # Event match check
    if body.event_id and row["event_id"] != body.event_id:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Ticket belongs to Event #{row['event_id']} ('{row['event_name']}'), not the selected event.",
        )

    # 1. Event Lifecycle Validation
    ev_status = row["event_status"]
    if ev_status not in CHECKIN_STATUSES:
        db.close()
        if ev_status == "draft":
            err_detail = "Cannot check in: Event is currently an unannounced draft."
        elif ev_status == "cancelled":
            err_detail = "Cannot check in: Event has been cancelled."
        elif ev_status == "completed":
            err_detail = "Cannot check in: Event has already completed."
        else:
            err_detail = f"Cannot check in: Event status is '{ev_status}'."
        raise HTTPException(status_code=400, detail=err_detail)

    # 2. Duplicate Check-in Validation
    if row["status"] == "attended":
        checkin_time_str = row["checkin_time"] or "earlier"
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Attendee '{row['name']}' is ALREADY CHECKED IN (verified at {checkin_time_str}). Duplicate check-in rejected.",
        )

    # 3. Registration Status Validations
    if row["status"] == "cancelled":
        db.close()
        raise HTTPException(status_code=400, detail="Cannot check in: Attendee registration was cancelled.")

    if row["status"] == "waitlisted":
        db.close()
        raise HTTPException(status_code=400, detail="Cannot check in: Attendee is currently on the waitlist.")

    if row["status"] != "registered":
        db.close()
        raise HTTPException(status_code=400, detail=f"Cannot check in: Attendee status is '{row['status']}'.")

    # 4. Perform Check-in & Store Attendance Audit Trail
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tkt_id = row["ticket_id"] or ticket_id or f"TKT{row['id']:04d}"

    db.execute(
        "UPDATE attendees SET status = 'attended', checkin_time = ? WHERE id = ?",
        (now_str, row["id"]),
    )
    if row["ticket_id"]:
        db.execute("UPDATE tickets SET status = 'used' WHERE ticket_id = ?", (row["ticket_id"],))

    # Insert into checkins audit table
    db.execute(
        """INSERT INTO checkins (event_id, attendee_id, ticket_id, checked_in_by, checkin_time, method)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (row["event_id"], row["id"], tkt_id, current_user["id"], now_str, "qr" if is_qr else "manual"),
    )

    # Write system audit log
    write_audit(
        db,
        actor=current_user,
        action="checkin.verify",
        object_type="attendee",
        object_id=row["id"],
        object_label=f"{row['name']} ({tkt_id})",
        previous_value={"status": row["status"]},
        new_value={"status": "attended", "checkin_time": now_str, "checked_in_by": current_user["name"], "method": "qr" if is_qr else "manual"},
    )

    # Notify attendee
    notify(
        db,
        row["user_id"],
        row["email"],
        row["event_id"],
        "🎫 Check-in Confirmed",
        f"Welcome to '{row['event_name']}'! Your check-in was verified by staff at {now_str}.",
        "checkin",
    )

    db.commit()
    db.close()

    return {
        "success": True,
        "message": f"Successfully checked in {row['name']}!",
        "attendee": {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "college": row["college"],
            "ticket_id": tkt_id,
            "event_name": row["event_name"],
            "checkin_time": now_str,
            "status": "attended",
            "checked_in_by": current_user["name"],
            "method": "qr" if is_qr else "manual",
        },
    }


@router.post("/{attendee_id}/checkin")
def manual_checkin(
    attendee_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    return verify_and_checkin(CheckinVerifyIn(attendee_id=attendee_id), current_user)


@router.post("/{attendee_id}/absent")
def mark_absent(
    attendee_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute(
        """SELECT a.id, a.event_id, a.name, e.organizer_id
           FROM attendees a JOIN events e ON a.event_id = e.id
           WHERE a.id = ?""",
        (attendee_id,),
    ).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Attendee not found")

    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You do not have permission to modify this attendee.")

    db.execute("UPDATE attendees SET status = 'absent' WHERE id = ?", (attendee_id,))
    write_audit(
        db,
        actor=current_user,
        action="attendee.mark_absent",
        object_type="attendee",
        object_id=attendee_id,
        object_label=row["name"],
        previous_value="registered",
        new_value="absent",
    )
    db.commit()
    db.close()
    return {"message": "Attendee marked as absent"}


@router.delete("/{attendee_id}")
def cancel_registration(
    attendee_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Cancel registration, free seat, promote waitlisted users, and write audit log."""
    db = get_db()
    row = db.execute(
        """SELECT a.*, e.organizer_id, e.name AS event_name
           FROM attendees a
           JOIN events e ON a.event_id = e.id
           WHERE a.id = ?""",
        (attendee_id,),
    ).fetchone()

    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Registration not found")

    # Authorization: Owner, Organizer of the event, or Admin can cancel
    is_owner = (row["user_id"] == current_user["id"]) or (row["email"].lower() == current_user["email"].lower())
    is_organizer = (row["organizer_id"] == current_user["id"])
    is_admin = (current_user["role"] == "admin")

    if not (is_owner or is_organizer or is_admin):
        db.close()
        raise HTTPException(status_code=403, detail="You are not authorized to cancel this registration.")

    was_active = (row["status"] in ["registered", "attended"])

    # Soft cancel
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE attendees SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
        (now_str, attendee_id),
    )
    db.execute("UPDATE tickets SET status = 'cancelled' WHERE attendee_id = ?", (attendee_id,))

    # Notification of cancellation
    notify(
        db,
        row["user_id"],
        row["email"],
        row["event_id"],
        "🚫 Registration Cancelled",
        f"Your registration for '{row['event_name']}' has been cancelled.",
        "cancellation",
    )

    write_audit(
        db,
        actor=current_user,
        action="registration.cancel",
        object_type="attendee",
        object_id=attendee_id,
        object_label=row["name"],
        previous_value={"status": row["status"]},
        new_value={"status": "cancelled", "cancelled_at": now_str},
    )

    # If seat was active, automatically promote next person on waitlist
    promotion_result = None
    if was_active:
        promotion_result = auto_promote_waitlist(db, row["event_id"])

    db.commit()
    db.close()

    msg = "Registration cancelled successfully."
    if promotion_result and promotion_result.get("promoted"):
        msg += f" Waitlisted participant '{promotion_result['name']}' has been automatically promoted to take this seat."

    return {
        "message": msg,
        "promoted_waitlist": promotion_result,
    }


# ── Attendance Audit Trail ────────────────────────────────────────────────────

@router.get("/checkins")
def get_checkin_logs(
    event_id: Optional[int] = None,
    limit: int = 100,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Retrieve verified check-in audit records with staff auditor details."""
    db = get_db()
    query = """
        SELECT c.id, c.event_id, c.attendee_id, c.ticket_id, c.checkin_time, c.method,
               e.name AS event_name,
               a.name AS attendee_name, a.email AS attendee_email, a.phone AS attendee_phone,
               u.name AS staff_name, u.role AS staff_role
        FROM checkins c
        JOIN events e ON c.event_id = e.id
        JOIN attendees a ON c.attendee_id = a.id
        LEFT JOIN users u ON c.checked_in_by = u.id
        WHERE 1=1
    """
    params = []
    if current_user["role"] != "admin":
        query += " AND e.organizer_id = ?"
        params.append(current_user["id"])

    if event_id:
        query += " AND c.event_id = ?"
        params.append(event_id)

    query += " ORDER BY c.checkin_time DESC, c.id DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]

