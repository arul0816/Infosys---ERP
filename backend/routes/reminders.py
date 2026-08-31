from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth import require_roles, get_current_user
from datetime import datetime, timedelta
import json

router = APIRouter()


class ReminderSettingsIn(BaseModel):
    enable_24h: Optional[bool] = True
    enable_1h: Optional[bool] = True


# ── Send Reminders (Manual Trigger for Testing) ───────────────────────────────

@router.post("/{event_id}/send")
def send_event_reminders(
    event_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Manually trigger reminders for an event (for testing)"""
    db = get_db()

    # Check event
    event = db.execute(
        "SELECT id, name, date, time, organizer_id FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get all registered attendees
    attendees = db.execute(
        """SELECT id, name, email, user_id FROM attendees
           WHERE event_id = ? AND status IN ('registered', 'attended')""",
        (event_id,),
    ).fetchall()

    sent_count = 0
    for attendee in attendees:
        # Insert reminder notification
        db.execute(
            """INSERT INTO notifications (user_id, email, event_id, title, message, type)
               VALUES (?, ?, ?, ?, ?, 'reminder')""",
            (attendee["user_id"], attendee["email"], event_id,
             f"🔔 Reminder: {event['name']} is coming up!",
             f"Don't forget! '{event['name']}' is scheduled for {event['date']} at {event['time']}."),
        )
        sent_count += 1

    db.commit()
    db.close()

    return {
        "event_id": event_id,
        "reminders_sent": sent_count,
        "message": f"Sent {sent_count} reminder notifications"
    }


# ── Get Upcoming Events (for Reminders) ────────────────────────────────────────

@router.get("/upcoming/24h")
def get_upcoming_events_24h(
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get events happening in the next 24 hours"""
    db = get_db()

    now = datetime.now()
    tomorrow = now + timedelta(hours=24)

    query = """
        SELECT id, name, date, time, organizer_id FROM events
        WHERE datetime(date || ' ' || time) > datetime(?)
        AND datetime(date || ' ' || time) <= datetime(?)
        AND status NOT IN ('cancelled', 'draft')
    """
    
    rows = db.execute(query, (now.isoformat(), tomorrow.isoformat())).fetchall()
    db.close()

    return [dict(r) for r in rows]


@router.get("/upcoming/1h")
def get_upcoming_events_1h(
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get events happening in the next 1 hour"""
    db = get_db()

    now = datetime.now()
    one_hour_later = now + timedelta(hours=1)

    query = """
        SELECT id, name, date, time, organizer_id FROM events
        WHERE datetime(date || ' ' || time) > datetime(?)
        AND datetime(date || ' ' || time) <= datetime(?)
        AND status NOT IN ('cancelled', 'draft')
    """
    
    rows = db.execute(query, (now.isoformat(), one_hour_later.isoformat())).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Process Reminders (Background Task) ───────────────────────────────────────

@router.post("/process-scheduled-reminders")
def process_scheduled_reminders(
    current_user: dict = Depends(require_roles(["admin"])),
):
    """
    Process all scheduled reminders.
    This endpoint should be called by a background task/cron job.
    Recommended: Every 5-10 minutes
    """
    db = get_db()

    now = datetime.now()
    sent_24h = 0
    sent_1h = 0

    # Process 24-hour reminders
    # Get events happening in approximately 24 hours (23-25 hour window)
    events_24h = db.execute("""
        SELECT e.id, e.name, e.date, e.time FROM events e
        WHERE datetime(e.date || ' ' || e.time) > datetime(?, '+23 hours')
        AND datetime(e.date || ' ' || e.time) < datetime(?, '+25 hours')
        AND e.status NOT IN ('cancelled', 'draft')
    """, (now.isoformat(), now.isoformat())).fetchall()

    for event in events_24h:
        # Get attendees who haven't been sent 24h reminder
        attendees = db.execute("""
            SELECT DISTINCT a.id, a.email, a.user_id FROM attendees a
            WHERE a.event_id = ?
            AND a.status IN ('registered', 'attended')
            AND NOT EXISTS (
                SELECT 1 FROM reminder_tracking rt
                WHERE rt.event_id = ?
                AND rt.user_id = a.user_id
                AND rt.reminder_type = '24h'
                AND rt.is_sent = 1
            )
        """, (event["id"], event["id"])).fetchall()

        for attendee in attendees:
            # Send notification
            db.execute(
                """INSERT INTO notifications (user_id, email, event_id, title, message, type)
                   VALUES (?, ?, ?, ?, ?, 'reminder')""",
                (attendee["user_id"], attendee["email"], event["id"],
                 f"🔔 Event Tomorrow: {event['name']}",
                 f"'{event['name']}' is happening tomorrow at {event['time']}."),
            )

            # Track that reminder was sent
            db.execute(
                """INSERT INTO reminder_tracking (event_id, user_id, email, reminder_type, scheduled_time, sent_at, is_sent)
                   VALUES (?, ?, ?, '24h', ?, ?, 1)""",
                (event["id"], attendee["user_id"], attendee["email"], now.isoformat(), now.isoformat()),
            )
            sent_24h += 1

    # Process 1-hour reminders
    # Get events happening in approximately 1 hour (50min - 70min window)
    events_1h = db.execute("""
        SELECT e.id, e.name, e.date, e.time FROM events e
        WHERE datetime(e.date || ' ' || e.time) > datetime(?, '+50 minutes')
        AND datetime(e.date || ' ' || e.time) < datetime(?, '+70 minutes')
        AND e.status NOT IN ('cancelled', 'draft')
    """, (now.isoformat(), now.isoformat())).fetchall()

    for event in events_1h:
        # Get attendees who haven't been sent 1h reminder
        attendees = db.execute("""
            SELECT DISTINCT a.id, a.email, a.user_id FROM attendees a
            WHERE a.event_id = ?
            AND a.status IN ('registered', 'attended')
            AND NOT EXISTS (
                SELECT 1 FROM reminder_tracking rt
                WHERE rt.event_id = ?
                AND rt.user_id = a.user_id
                AND rt.reminder_type = '1h'
                AND rt.is_sent = 1
            )
        """, (event["id"], event["id"])).fetchall()

        for attendee in attendees:
            # Send notification
            db.execute(
                """INSERT INTO notifications (user_id, email, event_id, title, message, type)
                   VALUES (?, ?, ?, ?, ?, 'reminder')""",
                (attendee["user_id"], attendee["email"], event["id"],
                 f"⏰ Event Starting Soon: {event['name']}",
                 f"'{event['name']}' starts in 1 hour at {event['time']}. Get ready!"),
            )

            # Track that reminder was sent
            db.execute(
                """INSERT INTO reminder_tracking (event_id, user_id, email, reminder_type, scheduled_time, sent_at, is_sent)
                   VALUES (?, ?, ?, '1h', ?, ?, 1)""",
                (event["id"], attendee["user_id"], attendee["email"], now.isoformat(), now.isoformat()),
            )
            sent_1h += 1

    db.commit()
    db.close()

    return {
        "status": "processed",
        "reminders_24h_sent": sent_24h,
        "reminders_1h_sent": sent_1h,
        "total_sent": sent_24h + sent_1h,
        "processed_at": now.isoformat()
    }


# ── Get Reminder Tracking ──────────────────────────────────────────────────────

@router.get("/{event_id}/tracking")
def get_reminder_tracking(
    event_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Get reminder tracking for an event"""
    db = get_db()

    # Check authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get tracking data
    rows = db.execute(
        """SELECT reminder_type, COUNT(*) as sent_count, COUNT(CASE WHEN is_sent = 1 THEN 1 END) as confirmed
           FROM reminder_tracking WHERE event_id = ?
           GROUP BY reminder_type""",
        (event_id,),
    ).fetchall()

    db.close()

    return {
        "event_id": event_id,
        "reminders": [dict(r) for r in rows]
    }
