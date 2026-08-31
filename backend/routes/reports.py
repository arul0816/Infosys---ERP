import io
import csv
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional
from database import get_db
from auth import require_roles

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

router = APIRouter()


def _fmt_inr(amount) -> str:
    return f"INR {float(amount or 0):,.2f}"


def _section_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    return table


def _build_event_pdf(event: dict, sections: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"EventSphere Report - {event['name']}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1e40af"),
        spaceBefore=14,
        spaceAfter=8,
    )

    story = []
    story.append(Paragraph("EventSphere Event Report", title_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} · Event ID {event['id']}",
        subtitle_style,
    ))
    story.append(Spacer(1, 0.1 * inch))

    # ── Event Overview ────────────────────────────────────────────────────────
    story.append(Paragraph("Event Overview", heading_style))
    overview = [
        ["Field", "Value"],
        ["Event Name", event["name"]],
        ["Date & Time", f"{event['date']} at {event['time']}"],
        ["Status", str(event["status"]).title()],
        ["Category / Type", f"{event.get('category') or 'General'} / {event.get('event_type') or 'Event'}"],
        ["Organizer", event.get("organizer_name") or "Unassigned"],
        ["Venue", event.get("venue_name") or ("Online" if event.get("is_online") else "Not assigned")],
        ["Capacity", str(event.get("capacity") or 100)],
    ]
    story.append(_section_table(overview, col_widths=[2.2 * inch, 4.3 * inch]))
    story.append(Spacer(1, 0.15 * inch))

    # ── Financial Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("Financial Summary", heading_style))
    fin = sections["financial"]
    financial = [
        ["Metric", "Amount"],
        ["Event Budget", _fmt_inr(fin["budget"])],
        ["Total Expenses", _fmt_inr(fin["expenses"])],
        ["Confirmed Sponsorship", _fmt_inr(fin["sponsorship"])],
        ["Remaining Budget", _fmt_inr(fin["remaining"])],
        ["Budget Utilization", f"{fin['utilization']:.1f}%"],
    ]
    story.append(_section_table(financial, col_widths=[2.5 * inch, 4.0 * inch]))

    if fin.get("expense_breakdown"):
        story.append(Spacer(1, 0.1 * inch))
        expense_rows = [["Category", "Amount"]] + [
            [row["category"], _fmt_inr(row["total"])]
            for row in fin["expense_breakdown"]
        ]
        story.append(_section_table(expense_rows, col_widths=[2.5 * inch, 4.0 * inch]))

    story.append(Spacer(1, 0.15 * inch))

    # ── Attendance ────────────────────────────────────────────────────────────
    story.append(Paragraph("Attendance & Registrations", heading_style))
    att = sections["attendance"]
    attendance = [
        ["Metric", "Count"],
        ["Total Registrations", str(att["total"])],
        ["Checked In", str(att["attended"])],
        ["Registered (Pending)", str(att["registered"])],
        ["Waitlisted", str(att["waitlisted"])],
        ["Absent / No-Show", str(att["absent"])],
        ["Cancelled", str(att["cancelled"])],
        ["Attendance Rate", f"{att['attendance_rate']:.1f}%"],
    ]
    story.append(_section_table(attendance, col_widths=[2.5 * inch, 4.0 * inch]))
    story.append(Spacer(1, 0.15 * inch))

    # ── Resources ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Allocated Resources", heading_style))
    resources = sections["resources"]
    if resources:
        resource_rows = [["Resource", "Quantity Used"]] + [
            [r["name"], str(r["quantity_used"])] for r in resources
        ]
        story.append(_section_table(resource_rows, col_widths=[3.5 * inch, 3.0 * inch]))
    else:
        story.append(Paragraph("No resources allocated to this event.", styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    # ── Vendors ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Contracted Vendors", heading_style))
    vendors = sections["vendors"]
    if vendors:
        vendor_rows = [["Vendor", "Service", "Contact", "Rating"]] + [
            [
                v["name"],
                v["service_type"],
                v["contact"] or "—",
                f"{v['rating']:.1f}" if v.get("rating") else "N/A",
            ]
            for v in vendors
        ]
        story.append(_section_table(vendor_rows, col_widths=[1.8 * inch, 1.5 * inch, 1.8 * inch, 1.4 * inch]))
    else:
        story.append(Paragraph("No vendors assigned to this event.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def _assert_event_access(db, event_id: int, current_user: dict):
    row = db.execute(
        "SELECT organizer_id FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return row


@router.get("")
@router.get("/")
def get_report(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        is_admin = current_user["role"] == "admin"
        organizer_id = current_user["id"]
        event_filter = "" if is_admin else " WHERE e.organizer_id = ?"
        params = [] if is_admin else [organizer_id]

        events = db.execute(f"""
            SELECT e.id, e.name, e.event_type, e.category, e.date, e.time, e.budget, e.status,
                   e.capacity, e.is_online, e.meeting_link,
                   v.name AS venue_name, v.location AS venue_location
            FROM events e
            LEFT JOIN venues v ON e.venue_id = v.id
            {event_filter}
            ORDER BY e.date DESC
        """, params).fetchall()

        report = []
        for ev in events:
            ev_dict = dict(ev)
            resources = db.execute("SELECT r.name, er.quantity_used FROM event_resources er JOIN resources r ON er.resource_id = r.id WHERE er.event_id = ?", (ev_dict["id"],)).fetchall()
            attendee_stats = db.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status='attended' THEN 1 ELSE 0 END) AS attended, SUM(CASE WHEN status='registered' THEN 1 ELSE 0 END) AS registered, SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) AS absent, SUM(CASE WHEN status='waitlisted' THEN 1 ELSE 0 END) AS waitlisted, SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS cancelled FROM attendees WHERE event_id = ?", (ev_dict["id"],)).fetchone()
            vendor_list = db.execute("SELECT v.name, v.service_type, v.contact, v.rating FROM vendor_assignments va JOIN vendors v ON va.vendor_id = v.id WHERE va.event_id = ?", (ev_dict["id"],)).fetchall()
            ev_dict["resources"] = [dict(r) for r in resources]
            ev_dict["attendees"] = dict(attendee_stats) if attendee_stats else {}
            ev_dict["vendors"] = [dict(v) for v in vendor_list]
            report.append(ev_dict)

        total_budget = sum((e["budget"] or 0) for e in report)
        total_attendees = db.execute("SELECT COUNT(*) FROM attendees" if is_admin else "SELECT COUNT(*) FROM attendees WHERE event_id IN (SELECT id FROM events WHERE organizer_id = ?)", () if is_admin else (organizer_id,)).fetchone()[0]
        total_vendors = db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
        return {"total_events": len(report), "total_budget": total_budget, "total_attendees": total_attendees, "total_vendors": total_vendors, "events": report}
    finally:
        db.close()


@router.get("/export/attendees")
def export_attendees_csv(event_id: Optional[int] = None, current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        is_admin = current_user["role"] == "admin"
        organizer_id = current_user["id"]
        query = "SELECT a.id AS attendee_id, t.ticket_id, a.name, a.email, a.phone, a.college, a.status, a.registered_at, a.checkin_time, e.id AS event_id, e.name AS event_name FROM attendees a JOIN events e ON a.event_id = e.id LEFT JOIN tickets t ON t.attendee_id = a.id WHERE 1=1"
        params = []
        if not is_admin:
            query += " AND e.organizer_id = ?"
            params.append(organizer_id)
        if event_id:
            query += " AND a.event_id = ?"
            params.append(event_id)
        query += " ORDER BY a.registered_at DESC"

        rows = db.execute(query, params).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket ID", "Attendee ID", "Participant Name", "Email", "Phone", "College / Organization", "Event ID", "Event Name", "Status", "Registered At", "Check-In Time"])
        for r in rows:
            writer.writerow([r["ticket_id"] or "N/A", r["attendee_id"], r["name"], r["email"], r["phone"], r["college"] or "", r["event_id"], r["event_name"], r["status"], r["registered_at"] or "", r["checkin_time"] or ""])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={'attendees_all' if not event_id else f'attendees_event_{event_id}'}.csv"})
    finally:
        db.close()


@router.get("/export/events")
def export_events_csv(current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        is_admin = current_user["role"] == "admin"
        organizer_id = current_user["id"]
        params = []
        query = "SELECT e.id, e.name, e.event_type, e.category, e.date, e.time, e.budget, e.capacity, e.status, e.is_online, v.name AS venue_name, (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'registered') AS registered, (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'attended') AS attended, (SELECT COUNT(*) FROM attendees a WHERE a.event_id = e.id AND a.status = 'waitlisted') AS waitlisted FROM events e LEFT JOIN venues v ON e.venue_id = v.id"
        if not is_admin:
            query += " WHERE e.organizer_id = ?"
            params.append(organizer_id)
        query += " ORDER BY e.date DESC"
        rows = db.execute(query, params).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Event ID", "Event Name", "Event Type", "Category", "Date", "Time", "Venue", "Budget (INR)", "Capacity", "Registered Count", "Attended Count", "Waitlisted Count", "Status", "Is Online"])
        for r in rows:
            writer.writerow([r["id"], r["name"], r["event_type"], r["category"] or "General", r["date"], r["time"], r["venue_name"] or "Unassigned", r["budget"], r["capacity"] or 100, r["registered"] or 0, r["attended"] or 0, r["waitlisted"] or 0, r["status"], "Yes" if r["is_online"] else "No"])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=events_report.csv"})
    finally:
        db.close()


@router.get("/events/{event_id}/pdf")
def export_event_pdf(event_id: int, current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        _assert_event_access(db, event_id, current_user)

        event = db.execute("""
            SELECT e.id, e.name, e.event_type, e.category, e.date, e.time, e.status,
                   e.budget, e.capacity, e.is_online,
                   v.name AS venue_name,
                   u.name AS organizer_name
            FROM events e
            LEFT JOIN venues v ON v.id = e.venue_id
            LEFT JOIN users u ON u.id = e.organizer_id
            WHERE e.id = ?
        """, (event_id,)).fetchone()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        stats = db.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='attended' THEN 1 ELSE 0 END) AS attended,
                SUM(CASE WHEN status='registered' THEN 1 ELSE 0 END) AS registered,
                SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) AS absent,
                SUM(CASE WHEN status='waitlisted' THEN 1 ELSE 0 END) AS waitlisted,
                SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS cancelled
            FROM attendees WHERE event_id = ?
        """, (event_id,)).fetchone()

        expense_total = db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE event_id = ?",
            (event_id,),
        ).fetchone()[0]
        sponsor_total = db.execute(
            "SELECT COALESCE(SUM(sponsorship_amount), 0) FROM sponsors WHERE event_id = ? AND status = 'confirmed'",
            (event_id,),
        ).fetchone()[0]
        budget_row = db.execute(
            "SELECT total_budget FROM budgets WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        budget_amount = budget_row["total_budget"] if budget_row else event["budget"]
        remaining = (budget_amount or 0) - (expense_total or 0)
        utilization = (expense_total / budget_amount * 100) if budget_amount else 0.0

        expense_breakdown = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses WHERE event_id = ? GROUP BY category ORDER BY total DESC",
            (event_id,),
        ).fetchall()

        resources = db.execute("""
            SELECT r.name, er.quantity_used
            FROM event_resources er
            JOIN resources r ON r.id = er.resource_id
            WHERE er.event_id = ?
        """, (event_id,)).fetchall()

        vendors = db.execute("""
            SELECT v.name, v.service_type, v.contact, v.rating
            FROM vendor_assignments va
            JOIN vendors v ON v.id = va.vendor_id
            WHERE va.event_id = ?
        """, (event_id,)).fetchall()

        total = stats["total"] or 0
        attended = stats["attended"] or 0
        attendance_rate = (attended / total * 100) if total else 0.0

        pdf_bytes = _build_event_pdf(
            dict(event),
            sections={
                "financial": {
                    "budget": budget_amount,
                    "expenses": expense_total,
                    "sponsorship": sponsor_total,
                    "remaining": remaining,
                    "utilization": utilization,
                    "expense_breakdown": [dict(r) for r in expense_breakdown],
                },
                "attendance": {
                    "total": total,
                    "attended": attended,
                    "registered": stats["registered"] or 0,
                    "absent": stats["absent"] or 0,
                    "waitlisted": stats["waitlisted"] or 0,
                    "cancelled": stats["cancelled"] or 0,
                    "attendance_rate": attendance_rate,
                },
                "resources": [dict(r) for r in resources],
                "vendors": [dict(v) for v in vendors],
            },
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=event_{event_id}_report.pdf"},
        )
    finally:
        db.close()


@router.get("/events/{event_id}/attendees/csv")
def export_event_attendees_csv(event_id: int, current_user: dict = Depends(require_roles(["admin", "organizer"]))):
    db = get_db()
    try:
        _assert_event_access(db, event_id, current_user)
        rows = db.execute("SELECT a.id AS attendee_id, a.name, a.email, a.phone, a.college, a.status, a.registered_at, t.ticket_id FROM attendees a LEFT JOIN tickets t ON t.attendee_id = a.id WHERE a.event_id = ? ORDER BY a.registered_at DESC", (event_id,)).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Attendee ID", "Name", "Email", "Phone", "College / Organization", "Status", "Registered At", "Ticket ID"])
        for r in rows:
            writer.writerow([r["attendee_id"], r["name"], r["email"], r["phone"], r["college"] or "", r["status"], r["registered_at"] or "", r["ticket_id"] or "N/A"])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=event_{event_id}_attendees.csv"})
    finally:
        db.close()
