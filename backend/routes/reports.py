import io
import csv
from fastapi import APIRouter, HTTPException, Depends, Response, Query
from typing import Optional
from database import get_db
from auth import get_current_user, require_roles

router = APIRouter()


@router.get("/")
def get_report(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    event_filter = "" if is_admin else f"WHERE e.organizer_id = {organizer_id}"

    events = db.execute(f"""
        SELECT e.id, e.name, e.event_type, e.category, e.date, e.time, e.budget, e.status,
               e.capacity, e.is_online, e.meeting_link,
               v.name AS venue_name, v.location AS venue_location
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.id
        {event_filter}
        ORDER BY e.date DESC
    """).fetchall()

    report = []
    for ev in events:
        ev_dict = dict(ev)

        resources = db.execute("""
            SELECT r.name, er.quantity_used
            FROM event_resources er
            JOIN resources r ON er.resource_id = r.id
            WHERE er.event_id = ?
        """, (ev_dict["id"],)).fetchall()

        attendee_stats = db.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status='attended'   THEN 1 ELSE 0 END) AS attended,
                   SUM(CASE WHEN status='registered' THEN 1 ELSE 0 END) AS registered,
                   SUM(CASE WHEN status='absent'     THEN 1 ELSE 0 END) AS absent,
                   SUM(CASE WHEN status='waitlisted' THEN 1 ELSE 0 END) AS waitlisted,
                   SUM(CASE WHEN status='cancelled'  THEN 1 ELSE 0 END) AS cancelled
            FROM attendees WHERE event_id = ?
        """, (ev_dict["id"],)).fetchone()

        vendor_list = db.execute("""
            SELECT v.name, v.service_type, v.contact, v.rating
            FROM vendor_assignments va
            JOIN vendors v ON va.vendor_id = v.id
            WHERE va.event_id = ?
        """, (ev_dict["id"],)).fetchall()

        ev_dict["resources"] = [dict(r) for r in resources]
        ev_dict["attendees"] = dict(attendee_stats) if attendee_stats else {}
        ev_dict["vendors"] = [dict(v) for v in vendor_list]
        report.append(ev_dict)

    total_budget = sum(e["budget"] for e in report)

    scope_attendee = "" if is_admin else f"WHERE event_id IN (SELECT id FROM events WHERE organizer_id = {organizer_id})"
    total_attendees = db.execute(f"SELECT COUNT(*) FROM attendees {scope_attendee}").fetchone()[0]
    total_vendors = db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    db.close()

    return {
        "total_events": len(report),
        "total_budget": total_budget,
        "total_attendees": total_attendees,
        "total_vendors": total_vendors,
        "events": report,
    }


# ── CSV Export Endpoints ──────────────────────────────────────────────────────

@router.get("/export/attendees")
def export_attendees_csv(
    event_id: Optional[int] = None,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    query = """
        SELECT a.id AS attendee_id, t.ticket_id, a.name, a.email, a.phone, a.college,
               a.status, a.registered_at, a.checkin_time,
               e.id AS event_id, e.name AS event_name
        FROM attendees a
        JOIN events e ON a.event_id = e.id
        LEFT JOIN tickets t ON t.attendee_id = a.id
        WHERE 1=1
    """
    params = []

    if not is_admin:
        query += " AND e.organizer_id = ?"
        params.append(organizer_id)

    if event_id:
        query += " AND a.event_id = ?"
        params.append(event_id)

    query += " ORDER BY a.registered_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Ticket ID",
        "Attendee ID",
        "Participant Name",
        "Email",
        "Phone",
        "College / Organization",
        "Event ID",
        "Event Name",
        "Status",
        "Registered At",
        "Check-In Time",
    ])

    for r in rows:
        writer.writerow([
            r["ticket_id"] or "N/A",
            r["attendee_id"],
            r["name"],
            r["email"],
            r["phone"],
            r["college"] or "",
            r["event_id"],
            r["event_name"],
            r["status"],
            r["registered_at"] or "",
            r["checkin_time"] or "",
        ])

    csv_content = output.getvalue()
    filename = f"attendees_{f'event_{event_id}' if event_id else 'all'}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/events")
def export_events_csv(
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    query = """
        SELECT e.id, e.name, e.event_type, e.category, e.date, e.time,
               e.budget, e.capacity, e.status, e.is_online,
               v.name AS venue_name,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'registered') AS registered,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'attended') AS attended,
               (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'waitlisted') AS waitlisted
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.id
    """
    params = []
    if not is_admin:
        query += " WHERE e.organizer_id = ?"
        params.append(organizer_id)

    query += " ORDER BY e.date DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID",
        "Event Name",
        "Event Type",
        "Category",
        "Date",
        "Time",
        "Venue",
        "Budget (INR)",
        "Capacity",
        "Registered Count",
        "Attended Count",
        "Waitlisted Count",
        "Status",
        "Is Online",
    ])

    for r in rows:
        writer.writerow([
            r["id"],
            r["name"],
            r["event_type"],
            r["category"] or "General",
            r["date"],
            r["time"],
            r["venue_name"] or "Unassigned",
            r["budget"],
            r["capacity"] or 100,
            r["registered"] or 0,
            r["attended"] or 0,
            r["waitlisted"] or 0,
            r["status"],
            "Yes" if r["is_online"] else "No",
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_report.csv"},
    )
