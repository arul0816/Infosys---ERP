import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database import get_db
from auth import get_current_user, require_roles

router = APIRouter()


@router.get("/summary")
def get_analytics_summary(
    range_days: Optional[str] = Query("30", alias="range"),
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    # Base filter for organizer vs admin
    event_filter = "" if is_admin else f"WHERE organizer_id = {organizer_id}"
    attendee_filter = "" if is_admin else f"WHERE event_id IN (SELECT id FROM events WHERE organizer_id = {organizer_id})"

    total_events = db.execute(f"SELECT COUNT(*) FROM events {event_filter}").fetchone()[0]
    total_venues = db.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
    total_resources = db.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    total_vendors = db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]

    # Registration counts
    total_registrations = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter}"
    ).fetchone()[0]

    active_registrations = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter} {'AND' if attendee_filter else 'WHERE'} status = 'registered'"
    ).fetchone()[0]

    attended_count = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter} {'AND' if attendee_filter else 'WHERE'} status = 'attended'"
    ).fetchone()[0]

    absent_count = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter} {'AND' if attendee_filter else 'WHERE'} status = 'absent'"
    ).fetchone()[0]

    waitlisted_count = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter} {'AND' if attendee_filter else 'WHERE'} status = 'waitlisted'"
    ).fetchone()[0]

    cancelled_count = db.execute(
        f"SELECT COUNT(*) FROM attendees {attendee_filter} {'AND' if attendee_filter else 'WHERE'} status = 'cancelled'"
    ).fetchone()[0]

    # Rates
    effective_total = attended_count + active_registrations + absent_count
    attendance_rate = round((attended_count / effective_total * 100), 1) if effective_total > 0 else 0.0
    cancellation_rate = round((cancelled_count / total_registrations * 100), 1) if total_registrations > 0 else 0.0
    checkin_rate = round((attended_count / (attended_count + active_registrations) * 100), 1) if (attended_count + active_registrations) > 0 else 0.0

    # Capacity utilization across all events
    cap_query = f"SELECT SUM(capacity) AS total_cap, SUM((SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status IN ('registered', 'attended'))) AS filled FROM events e {event_filter}"
    cap_row = db.execute(cap_query).fetchone()
    total_capacity = cap_row["total_cap"] or 0
    total_filled = cap_row["filled"] or 0
    capacity_utilization = round((total_filled / total_capacity * 100), 1) if total_capacity > 0 else 0.0

    # Total budget
    budget_row = db.execute(f"SELECT SUM(budget) FROM events {event_filter}").fetchone()
    total_budget = budget_row[0] or 0.0

    db.close()

    return {
        "total_events": total_events,
        "total_venues": total_venues,
        "total_resources": total_resources,
        "total_vendors": total_vendors,
        "total_registrations": total_registrations,
        "active_registrations": active_registrations,
        "attended_count": attended_count,
        "absent_count": absent_count,
        "waitlisted_count": waitlisted_count,
        "cancelled_count": cancelled_count,
        "attendance_rate": attendance_rate,
        "cancellation_rate": cancellation_rate,
        "checkin_rate": checkin_rate,
        "total_capacity": total_capacity,
        "capacity_utilization": capacity_utilization,
        "total_budget": total_budget,
    }


@router.get("/registrations-over-time")
def get_registrations_over_time(
    range_days: Optional[str] = Query("30", alias="range"),
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    attendee_scope = "" if is_admin else f"AND a.event_id IN (SELECT id FROM events WHERE organizer_id = {organizer_id})"

    # Determine date cutoff
    days_map = {"7": 7, "30": 30, "90": 90, "all": 3650}
    days = days_map.get(range_days.lower(), 30)

    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

    query = f"""
        SELECT substr(a.registered_at, 1, 10) AS reg_date,
               COUNT(*) AS count,
               SUM(CASE WHEN a.status = 'attended' THEN 1 ELSE 0 END) AS attended_count
        FROM attendees a
        WHERE a.registered_at >= ? {attendee_scope}
        GROUP BY reg_date
        ORDER BY reg_date ASC
    """
    rows = db.execute(query, (cutoff,)).fetchall()
    db.close()

    # Fill in date gaps if needed or return list
    return [{"date": r["reg_date"], "registrations": r["count"], "attended": r["attended_count"]} for r in rows]


@router.get("/category-distribution")
def get_category_distribution(
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    scope = "" if is_admin else f"WHERE e.organizer_id = {organizer_id}"

    query = f"""
        SELECT COALESCE(e.category, 'Other') AS category,
               COUNT(DISTINCT e.id) AS event_count,
               COUNT(a.id) AS registration_count
        FROM events e
        LEFT JOIN attendees a ON a.event_id = e.id AND a.status != 'cancelled'
        {scope}
        GROUP BY category
        ORDER BY registration_count DESC
    """
    rows = db.execute(query).fetchall()
    db.close()

    return [{"category": r["category"], "events": r["event_count"], "registrations": r["registration_count"]} for r in rows]


@router.get("/top-events")
def get_top_events(
    limit: int = 5,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    scope = "" if is_admin else f"WHERE e.organizer_id = {organizer_id}"

    query = f"""
        SELECT e.id, e.name, e.category, e.date, e.capacity,
               COUNT(CASE WHEN a.status IN ('registered', 'attended') THEN 1 END) AS registered,
               COUNT(CASE WHEN a.status = 'attended' THEN 1 END) AS attended,
               COUNT(CASE WHEN a.status = 'waitlisted' THEN 1 END) AS waitlisted
        FROM events e
        LEFT JOIN attendees a ON a.event_id = e.id
        {scope}
        GROUP BY e.id
        ORDER BY registered DESC
        LIMIT ?
    """
    rows = db.execute(query, (limit,)).fetchall()
    db.close()

    result = []
    for r in rows:
        d = dict(r)
        cap = d["capacity"] or 100
        d["utilization"] = round((d["registered"] / cap * 100), 1) if cap > 0 else 0.0
        result.append(d)
    return result


@router.get("/attendance-breakdown")
def get_attendance_breakdown(
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    is_admin = current_user["role"] == "admin"
    organizer_id = current_user["id"]

    scope = "" if is_admin else f"WHERE event_id IN (SELECT id FROM events WHERE organizer_id = {organizer_id})"

    query = f"""
        SELECT status, COUNT(*) AS count
        FROM attendees
        {scope}
        GROUP BY status
    """
    rows = db.execute(query).fetchall()
    db.close()

    return [{"status": r["status"], "count": r["count"]} for r in rows]
