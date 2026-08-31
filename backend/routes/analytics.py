import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database import get_db
from auth import require_roles

router = APIRouter()


def _safe_percent(numerator: float, denominator: float) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


@router.get("/summary")
def get_analytics_summary(
    range_days: Optional[str] = Query("30", alias="range"),
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    try:
        event_filter = "" if current_user["role"] == "admin" else " WHERE organizer_id = ?"
        attendee_filter = "" if current_user["role"] == "admin" else " WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)"
        params = [] if current_user["role"] == "admin" else [current_user["id"]]

        def attendee_status_count(status: str):
            if attendee_filter:
                return db.execute(
                    f"SELECT COUNT(*) FROM attendees{attendee_filter} AND status = ?",
                    (*params, status),
                ).fetchone()[0]
            return db.execute(
                "SELECT COUNT(*) FROM attendees WHERE status = ?",
                (status,),
            ).fetchone()[0]

        total_events = db.execute(f"SELECT COUNT(*) FROM events{event_filter}", params).fetchone()[0]
        total_venues = db.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
        total_resources = db.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        total_vendors = db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]

        total_registrations = db.execute(f"SELECT COUNT(*) FROM attendees{attendee_filter}", params).fetchone()[0]
        active_registrations = attendee_status_count("registered")
        attended_count = attendee_status_count("attended")
        absent_count = attendee_status_count("absent")
        waitlisted_count = attendee_status_count("waitlisted")
        cancelled_count = attendee_status_count("cancelled")

        effective_total = attended_count + active_registrations + absent_count
        attendance_rate = _safe_percent(attended_count, effective_total)
        cancellation_rate = _safe_percent(cancelled_count, total_registrations)
        checkin_rate = _safe_percent(attended_count, attended_count + active_registrations)

        cap_row = db.execute(
            f"SELECT COALESCE(SUM(capacity), 0) AS total_cap, COALESCE(SUM((SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status IN ('registered','attended'))), 0) AS filled FROM events e{event_filter}",
            params,
        ).fetchone()
        total_capacity = cap_row["total_cap"] or 0
        total_filled = cap_row["filled"] or 0
        capacity_utilization = _safe_percent(total_filled, total_capacity)

        budget_total = db.execute(f"SELECT COALESCE(SUM(budget), 0) FROM events{event_filter}", params).fetchone()[0]
        total_expenses = db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE event_id IN (SELECT id FROM events)" if current_user["role"] == "admin" else "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)",
            () if current_user["role"] == "admin" else (current_user["id"],),
        ).fetchone()[0]

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
            "total_budget": budget_total,
            "total_expenses": total_expenses,
            "remaining_budget": budget_total - total_expenses,
        }
    finally:
        db.close()


@router.get("/overview")
def get_analytics_overview(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            total_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_registrations = db.execute("SELECT COUNT(*) FROM attendees").fetchone()[0]
            total_attendance = db.execute("SELECT COUNT(*) FROM attendees WHERE status = 'attended'").fetchone()[0]
            total_budget = db.execute("SELECT COALESCE(SUM(budget),0) FROM events").fetchone()[0]
            total_expenses = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
            sponsors_count = db.execute("SELECT COUNT(*) FROM sponsors").fetchone()[0]
            sponsorship_revenue = db.execute("SELECT COALESCE(SUM(sponsorship_amount),0) FROM sponsors WHERE status = 'confirmed'").fetchone()[0]
            upcoming_events = db.execute("SELECT COUNT(*) FROM events WHERE date >= date('now')").fetchone()[0]
            completed_events = db.execute("SELECT COUNT(*) FROM events WHERE status = 'completed'").fetchone()[0]
            top_events = db.execute("SELECT e.id, e.name, e.date, COUNT(a.id) AS registrations FROM events e LEFT JOIN attendees a ON a.event_id = e.id GROUP BY e.id ORDER BY registrations DESC LIMIT 5").fetchall()
        else:
            organizer_id = current_user["id"]
            total_events = db.execute("SELECT COUNT(*) FROM events WHERE organizer_id = ?", (organizer_id,)).fetchone()[0]
            total_registrations = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)", (organizer_id,)).fetchone()[0]
            total_attendance = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?) AND status = 'attended'", (organizer_id,)).fetchone()[0]
            total_budget = db.execute("SELECT COALESCE(SUM(budget),0) FROM events WHERE organizer_id = ?", (organizer_id,)).fetchone()[0]
            total_expenses = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)", (organizer_id,)).fetchone()[0]
            sponsors_count = db.execute("SELECT COUNT(*) FROM sponsors s JOIN events e ON s.event_id=e.id WHERE e.organizer_id = ?", (organizer_id,)).fetchone()[0]
            sponsorship_revenue = db.execute("SELECT COALESCE(SUM(s.sponsorship_amount),0) FROM sponsors s JOIN events e ON s.event_id=e.id WHERE e.organizer_id = ? AND s.status='confirmed'", (organizer_id,)).fetchone()[0]
            upcoming_events = db.execute("SELECT COUNT(*) FROM events WHERE organizer_id = ? AND date >= date('now')", (organizer_id,)).fetchone()[0]
            completed_events = db.execute("SELECT COUNT(*) FROM events WHERE organizer_id = ? AND status = 'completed'", (organizer_id,)).fetchone()[0]
            top_events = db.execute("SELECT e.id, e.name, e.date, COUNT(a.id) AS registrations FROM events e LEFT JOIN attendees a ON a.event_id = e.id WHERE e.organizer_id = ? GROUP BY e.id ORDER BY registrations DESC LIMIT 5", (organizer_id,)).fetchall()

        attendance_rate = _safe_percent(total_attendance, total_registrations)
        budget_utilization = _safe_percent(total_expenses, total_budget)
        resource_total = db.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        allocated = db.execute("SELECT COALESCE(SUM(quantity_used),0) FROM event_resources").fetchone()[0]
        avg_vendor_rating = db.execute("SELECT COALESCE(ROUND(AVG(overall_rating),2),0) FROM vendor_performance").fetchone()[0]

        return {
            "kpis": {
                "total_events": total_events,
                "upcoming_events": upcoming_events,
                "completed_events": completed_events,
                "total_registrations": total_registrations,
                "total_attendance": total_attendance,
                "attendance_rate": attendance_rate,
                "total_budget": total_budget,
                "total_expenses": total_expenses,
                "remaining_budget": total_budget - total_expenses,
                "budget_utilization": budget_utilization,
                "total_sponsors": sponsors_count,
                "sponsorship_revenue": sponsorship_revenue,
                "resource_utilization": _safe_percent(allocated, resource_total or 1),
                "avg_vendor_rating": avg_vendor_rating,
                "total_events": total_events,
            },
            "top_events": [dict(r) for r in top_events],
        }
    finally:
        db.close()


@router.get("/attendance")
def get_attendance_analytics(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            all_reg = db.execute("SELECT COUNT(*) FROM attendees").fetchone()[0]
            checked_in = db.execute("SELECT COUNT(*) FROM attendees WHERE status = 'attended'").fetchone()[0]
            no_show = db.execute("SELECT COUNT(*) FROM attendees WHERE status = 'absent'").fetchone()[0]
            registered = db.execute("SELECT COUNT(*) FROM attendees WHERE status = 'registered'").fetchone()[0]
        else:
            organizer_id = current_user["id"]
            all_reg = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)", (organizer_id,)).fetchone()[0]
            checked_in = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?) AND status = 'attended'", (organizer_id,)).fetchone()[0]
            no_show = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?) AND status = 'absent'", (organizer_id,)).fetchone()[0]
            registered = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?) AND status = 'registered'", (organizer_id,)).fetchone()[0]

        return {
            "registered": registered,
            "checked_in": checked_in,
            "no_show": no_show,
            "attendance_rate": _safe_percent(checked_in, all_reg if all_reg > 0 else 1),
            "total_registered": all_reg,
        }
    finally:
        db.close()


@router.get("/budget")
def get_budget_analytics(event_id: Optional[int] = None, current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if event_id is not None:
            event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not authorized")

            total_budget = db.execute("SELECT COALESCE(SUM(total_budget), 0) FROM budgets WHERE event_id = ?", (event_id,)).fetchone()[0]
            total_expenses = db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE event_id = ?", (event_id,)).fetchone()[0]
            sponsorship_revenue = db.execute("SELECT COALESCE(SUM(sponsorship_amount), 0) FROM sponsors WHERE event_id = ? AND status = 'confirmed'", (event_id,)).fetchone()[0]
            category_rows = db.execute("SELECT category, SUM(amount) AS total FROM expenses WHERE event_id = ? GROUP BY category ORDER BY total DESC", (event_id,)).fetchall()
            return {
                "event_id": event_id,
                "total_budget": total_budget,
                "total_expenses": total_expenses,
                "remaining_budget": total_budget - total_expenses,
                "budget_utilization": _safe_percent(total_expenses, total_budget),
                "sponsorship_revenue": sponsorship_revenue,
                "expenses_by_category": [dict(r) for r in category_rows],
            }

        if current_user["role"] == "admin":
            rows = db.execute("SELECT e.id, e.name, COALESCE(b.total_budget, 0) AS total_budget, COALESCE(SUM(ex.amount), 0) AS total_expenses FROM events e LEFT JOIN budgets b ON b.event_id = e.id LEFT JOIN expenses ex ON ex.event_id = e.id GROUP BY e.id ORDER BY e.date DESC").fetchall()
        else:
            rows = db.execute("SELECT e.id, e.name, COALESCE(b.total_budget, 0) AS total_budget, COALESCE(SUM(ex.amount), 0) AS total_expenses FROM events e LEFT JOIN budgets b ON b.event_id = e.id LEFT JOIN expenses ex ON ex.event_id = e.id WHERE e.organizer_id = ? GROUP BY e.id ORDER BY e.date DESC", (current_user["id"],)).fetchall()

        return {
            "total_budget": sum((r["total_budget"] or 0) for r in rows),
            "total_expenses": sum((r["total_expenses"] or 0) for r in rows),
            "events": [dict(r) for r in rows],
        }
    finally:
        db.close()


@router.get("/vendors")
def get_vendor_analytics(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        rows = db.execute("SELECT v.id, v.name, ROUND(AVG(vp.overall_rating), 2) AS avg_overall, ROUND(AVG(vp.quality_rating), 2) AS avg_quality, ROUND(AVG(vp.timeliness_rating), 2) AS avg_timeliness, ROUND(AVG(vp.cost_rating), 2) AS avg_cost, ROUND(AVG(vp.communication_rating), 2) AS avg_communication, COUNT(vp.id) AS rating_count FROM vendors v LEFT JOIN vendor_performance vp ON vp.vendor_id = v.id GROUP BY v.id ORDER BY avg_overall DESC").fetchall()
        if not rows:
            return {"avg_quality": 0, "avg_timeliness": 0, "avg_cost": 0, "avg_communication": 0, "avg_overall_rating": 0, "vendor_comparison": []}
        return {
            "avg_quality": round(sum((r["avg_quality"] or 0) for r in rows) / len(rows), 2),
            "avg_timeliness": round(sum((r["avg_timeliness"] or 0) for r in rows) / len(rows), 2),
            "avg_cost": round(sum((r["avg_cost"] or 0) for r in rows) / len(rows), 2),
            "avg_communication": round(sum((r["avg_communication"] or 0) for r in rows) / len(rows), 2),
            "avg_overall_rating": round(sum((r["avg_overall"] or 0) for r in rows) / len(rows), 2),
            "vendor_comparison": [dict(r) for r in rows],
        }
    finally:
        db.close()


@router.get("/resources")
def get_resource_analytics(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        total_available = db.execute("SELECT COALESCE(SUM(quantity), 0) FROM resources").fetchone()[0]
        allocated = db.execute("SELECT COALESCE(SUM(quantity_used), 0) FROM event_resources").fetchone()[0]
        by_event = db.execute("SELECT e.name AS event_name, COALESCE(SUM(er.quantity_used), 0) AS used FROM event_resources er JOIN events e ON e.id = er.event_id GROUP BY e.id ORDER BY used DESC").fetchall()
        by_resource = db.execute("SELECT r.name AS resource_name, COALESCE(SUM(er.quantity_used), 0) AS used FROM event_resources er JOIN resources r ON r.id = er.resource_id GROUP BY r.id ORDER BY used DESC").fetchall()
        recommendations = []
        reuse_suggestions = []
        for row in db.execute("SELECT id, name, quantity FROM resources ORDER BY name").fetchall():
            used = db.execute("SELECT COALESCE(SUM(quantity_used), 0) FROM event_resources WHERE resource_id = ?", (row["id"],)).fetchone()[0]
            remaining = (row["quantity"] or 0) - (used or 0)
            if remaining > 0:
                recommendations.append({"resource": row["name"], "message": f"{row['name']} has {remaining} units available for reuse this cycle."})

        # Suggest cross-event reuse when same resource is allocated to events at different times
        reuse_rows = db.execute("""
            SELECT r.name AS resource_name,
                   e1.name AS event_a, e1.date AS date_a, e1.time AS time_a,
                   e2.name AS event_b, e2.date AS date_b, e2.time AS time_b
            FROM event_resources er1
            JOIN event_resources er2 ON er1.resource_id = er2.resource_id AND er1.event_id < er2.event_id
            JOIN resources r ON r.id = er1.resource_id
            JOIN events e1 ON e1.id = er1.event_id
            JOIN events e2 ON e2.id = er2.event_id
            WHERE e1.date != e2.date OR e1.time != e2.time
            LIMIT 10
        """).fetchall()
        for row in reuse_rows:
            reuse_suggestions.append({
                "resource": row["resource_name"],
                "message": (
                    f"Reuse {row['resource_name']}: '{row['event_a']}' ({row['date_a']} {row['time_a']}) "
                    f"→ '{row['event_b']}' ({row['date_b']} {row['time_b']}) instead of allocating duplicate units."
                ),
            })

        return {
            "total_resources": total_available,
            "allocated_resources": allocated,
            "available_resources": max(total_available - allocated, 0),
            "resource_utilization": _safe_percent(allocated, total_available),
            "usage_by_event": [dict(r) for r in by_event],
            "usage_by_resource": [dict(r) for r in by_resource],
            "recommendations": recommendations,
            "reuse_suggestions": reuse_suggestions,
        }
    finally:
        db.close()


@router.get("/event-comparison")
def get_event_comparison(event_ids: Optional[str] = Query(None), current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            base_query = "SELECT id FROM events ORDER BY date DESC LIMIT 4"
            params = ()
        else:
            base_query = "SELECT id FROM events WHERE organizer_id = ? ORDER BY date DESC LIMIT 4"
            params = (current_user["id"],)

        if event_ids:
            parsed_ids = [int(x.strip()) for x in event_ids.split(",") if x.strip()]
        else:
            parsed_ids = [row["id"] for row in db.execute(base_query, params).fetchall()]

        if len(parsed_ids) < 1:
            raise HTTPException(status_code=400, detail="Select at least one event to compare.")

        rows = []
        for event_id in parsed_ids[:4]:
            event = db.execute("SELECT id, name, date, budget FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event:
                continue
            registration_count = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id = ?", (event_id,)).fetchone()[0]
            attended_count = db.execute("SELECT COUNT(*) FROM attendees WHERE event_id = ? AND status = 'attended'", (event_id,)).fetchone()[0]
            expense_total = db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE event_id = ?", (event_id,)).fetchone()[0]
            rating = db.execute("SELECT COALESCE(AVG(overall_rating), 0) FROM vendor_performance WHERE event_id = ?", (event_id,)).fetchone()[0]
            rows.append({
                "event_id": event["id"],
                "name": event["name"],
                "date": event["date"],
                "registrations": registration_count,
                "attendance_rate": _safe_percent(attended_count, registration_count if registration_count else 1),
                "budget": event["budget"],
                "expenses": expense_total,
                "remaining": (event["budget"] or 0) - expense_total,
                "vendor_rating": round(rating or 0, 2),
            })

        return {"events": rows}
    finally:
        db.close()


@router.get("/forecast")
def get_forecast(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            history_rows = db.execute("SELECT e.id, e.name, COUNT(a.id) AS registrations FROM events e LEFT JOIN attendees a ON a.event_id = e.id GROUP BY e.id ORDER BY e.date DESC LIMIT 6").fetchall()
        else:
            history_rows = db.execute("SELECT e.id, e.name, COUNT(a.id) AS registrations FROM events e LEFT JOIN attendees a ON a.event_id = e.id WHERE e.organizer_id = ? GROUP BY e.id ORDER BY e.date DESC LIMIT 6", (current_user["id"],)).fetchall()

        values = [row["registrations"] for row in history_rows if row["registrations"] is not None]
        if not values:
            return {"forecast": {"predicted_attendees": 0, "confidence": "low", "message": "Not enough historical data to forecast attendance."}, "history": []}
        predicted = round(sum(values) / len(values), 0)
        confidence = "high" if len(values) >= 3 else "medium" if len(values) >= 2 else "low"
        predicted_int = int(predicted)
        return {
            "forecast": {
                "predicted_attendees": predicted_int,
                "confidence": confidence,
                "basis": "Average historical registration volume across recent events.",
                "message": "Forecast is an estimate based on historical registrations and should be treated as planning guidance.",
                "recommendations": {
                    "venue_capacity": int(predicted_int * 1.15),
                    "chairs_needed": predicted_int,
                    "food_servings": int(predicted_int * 0.85),
                    "volunteers": max(2, round(predicted_int / 100)),
                    "registration_counters": max(1, round(predicted_int / 200)),
                },
            },
            "history": [dict(r) for r in history_rows],
        }
    finally:
        db.close()


@router.get("/registrations-over-time")
def get_registrations_over_time(range_days: Optional[str] = Query("30", alias="range"), current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        days_map = {"7": 7, "30": 30, "90": 90, "all": 3650}
        days = days_map.get((range_days or "30").lower(), 30)
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        if current_user["role"] == "admin":
            rows = db.execute("SELECT substr(a.registered_at, 1, 10) AS reg_date, COUNT(*) AS count, SUM(CASE WHEN a.status='attended' THEN 1 ELSE 0 END) AS attended_count FROM attendees a WHERE a.registered_at >= ? GROUP BY reg_date ORDER BY reg_date ASC", (cutoff,)).fetchall()
        else:
            rows = db.execute("SELECT substr(a.registered_at, 1, 10) AS reg_date, COUNT(*) AS count, SUM(CASE WHEN a.status='attended' THEN 1 ELSE 0 END) AS attended_count FROM attendees a WHERE a.registered_at >= ? AND a.event_id IN (SELECT id FROM events WHERE organizer_id = ?) GROUP BY reg_date ORDER BY reg_date ASC", (cutoff, current_user["id"])).fetchall()
        return [{"date": r["reg_date"], "registrations": r["count"], "attended": r["attended_count"]} for r in rows]
    finally:
        db.close()


@router.get("/category-distribution")
def get_category_distribution(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            rows = db.execute("SELECT COALESCE(e.category, 'Other') AS category, COUNT(DISTINCT e.id) AS event_count, COUNT(a.id) AS registration_count FROM events e LEFT JOIN attendees a ON a.event_id=e.id AND a.status != 'cancelled' GROUP BY category ORDER BY registration_count DESC").fetchall()
        else:
            rows = db.execute("SELECT COALESCE(e.category, 'Other') AS category, COUNT(DISTINCT e.id) AS event_count, COUNT(a.id) AS registration_count FROM events e LEFT JOIN attendees a ON a.event_id=e.id AND a.status != 'cancelled' WHERE e.organizer_id = ? GROUP BY category ORDER BY registration_count DESC", (current_user["id"],)).fetchall()
        return [{"category": r["category"], "events": r["event_count"], "registrations": r["registration_count"]} for r in rows]
    finally:
        db.close()


@router.get("/top-events")
def get_top_events(limit: int = 5, current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            rows = db.execute("SELECT e.id, e.name, e.category, e.date, e.capacity, COUNT(CASE WHEN a.status IN ('registered','attended') THEN 1 END) AS registered, COUNT(CASE WHEN a.status='attended' THEN 1 END) AS attended, COUNT(CASE WHEN a.status='waitlisted' THEN 1 END) AS waitlisted FROM events e LEFT JOIN attendees a ON a.event_id=e.id GROUP BY e.id ORDER BY registered DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = db.execute("SELECT e.id, e.name, e.category, e.date, e.capacity, COUNT(CASE WHEN a.status IN ('registered','attended') THEN 1 END) AS registered, COUNT(CASE WHEN a.status='attended' THEN 1 END) AS attended, COUNT(CASE WHEN a.status='waitlisted' THEN 1 END) AS waitlisted FROM events e LEFT JOIN attendees a ON a.event_id=e.id WHERE e.organizer_id = ? GROUP BY e.id ORDER BY registered DESC LIMIT ?", (current_user["id"], limit)).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            cap = item["capacity"] or 100
            item["utilization"] = round((item["registered"] / cap * 100), 1) if cap > 0 else 0.0
            result.append(item)
        return result
    finally:
        db.close()


@router.get("/attendance-breakdown")
def get_attendance_breakdown(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        if current_user["role"] == "admin":
            rows = db.execute("SELECT status, COUNT(*) AS count FROM attendees GROUP BY status").fetchall()
        else:
            rows = db.execute("SELECT a.status, COUNT(*) AS count FROM attendees a JOIN events e ON e.id = a.event_id WHERE e.organizer_id = ? GROUP BY a.status", (current_user["id"],)).fetchall()
        return [{"status": r["status"], "count": r["count"]} for r in rows]
    finally:
        db.close()


@router.get("/audit-logs")
def get_audit_logs(
    object_type: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_roles(["admin"])),
):
    """Retrieve system audit logs for administrative compliance and tracking."""
    db = get_db()
    try:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if object_type and object_type != "All":
            query += " AND LOWER(object_type) = LOWER(?)"
            params.append(object_type.strip())
        if action and action != "All":
            query += " AND action LIKE ?"
            params.append(f"%{action.strip()}%")
        if search:
            query += " AND (actor_name LIKE ? OR object_label LIKE ? OR action LIKE ? OR previous_value LIKE ? OR new_value LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term, term, term])
        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

