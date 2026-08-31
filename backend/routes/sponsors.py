from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from database import get_db
from auth import require_roles

router = APIRouter()

SPONSORSHIP_TYPES = ["Platinum", "Gold", "Silver", "Bronze", "In-kind"]
SPONSOR_STATUSES = ["pending", "approved", "rejected", "confirmed"]


class SponsorIn(BaseModel):
    sponsor_name: str = Field(..., min_length=2)
    contact_person: Optional[str] = ""
    contact_email: Optional[str] = ""
    contact_phone: Optional[str] = ""
    sponsorship_amount: float = Field(..., ge=0)
    sponsorship_type: Optional[str] = "Gold"
    status: Optional[str] = "pending"
    notes: Optional[str] = ""


class SponsorUpdate(BaseModel):
    sponsor_name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    sponsorship_amount: Optional[float] = None
    sponsorship_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ── Create Sponsor ────────────────────────────────────────────────────────────

@router.post("/{event_id}/sponsors", status_code=201)
def create_sponsor(
    event_id: int,
    sponsor_data: SponsorIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Add a sponsor to an event"""
    db = get_db()

    # Validate event exists
    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Check authorization
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized to manage this event")

    # Validate sponsorship type
    if sponsor_data.sponsorship_type and sponsor_data.sponsorship_type not in SPONSORSHIP_TYPES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {', '.join(SPONSORSHIP_TYPES)}")

    # Validate amount
    if sponsor_data.sponsorship_amount < 0:
        db.close()
        raise HTTPException(status_code=400, detail="Sponsorship amount cannot be negative")

    # Validate status
    status = sponsor_data.status or "pending"
    if status not in SPONSOR_STATUSES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(SPONSOR_STATUSES)}")

    # Create sponsor
    cur = db.execute(
        """INSERT INTO sponsors (event_id, sponsor_name, contact_person, contact_email, contact_phone,
                                 sponsorship_amount, sponsorship_type, status, notes, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_id, sponsor_data.sponsor_name, sponsor_data.contact_person, sponsor_data.contact_email,
         sponsor_data.contact_phone, sponsor_data.sponsorship_amount, sponsor_data.sponsorship_type or "Gold",
         status, sponsor_data.notes, current_user["id"]),
    )
    db.commit()
    sponsor_id = cur.lastrowid

    # Auto-create approval request for pending sponsors
    if status == "pending":
        db.execute(
            """INSERT INTO approvals (event_id, requester_id, request_type, reference_id, amount, reason, status)
               VALUES (?, ?, 'sponsorship', ?, ?, ?, 'pending')""",
            (event_id, current_user["id"], sponsor_id, sponsor_data.sponsorship_amount,
             f"Sponsorship from {sponsor_data.sponsor_name}"),
        )
        db.commit()

    db.close()

    return {
        "id": sponsor_id,
        "event_id": event_id,
        **sponsor_data.model_dump(),
        "message": "Sponsor added successfully"
    }


# ── Get Sponsors for Event ────────────────────────────────────────────────────

@router.get("/{event_id}/sponsors")
def get_sponsors(
    event_id: int,
    status: Optional[str] = None,
    sponsor_type: Optional[str] = Query(None, alias="type"),
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get all sponsors for an event"""
    db = get_db()

    # Validate event exists and authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    query = "SELECT * FROM sponsors WHERE event_id = ?"
    params = [event_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    if sponsor_type:
        query += " AND sponsorship_type = ?"
        params.append(sponsor_type)

    query += " ORDER BY sponsorship_amount DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Get Single Sponsor ────────────────────────────────────────────────────────

@router.get("/sponsor/{sponsor_id}")
def get_sponsor(
    sponsor_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get a single sponsor"""
    db = get_db()

    sponsor = db.execute("SELECT * FROM sponsors WHERE id = ?", (sponsor_id,)).fetchone()
    if not sponsor:
        db.close()
        raise HTTPException(status_code=404, detail="Sponsor not found")

    # Authorization
    if current_user and current_user["role"] != "admin":
        event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (sponsor["event_id"],)).fetchone()
        if event["organizer_id"] != current_user["id"]:
            db.close()
            raise HTTPException(status_code=403, detail="Not authorized")

    db.close()
    return dict(sponsor)


# ── Update Sponsor ────────────────────────────────────────────────────────────

@router.put("/{event_id}/sponsors/{sponsor_id}")
def update_sponsor(
    event_id: int,
    sponsor_id: int,
    sponsor_data: SponsorUpdate,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Update a sponsor"""
    db = get_db()

    sponsor = db.execute(
        "SELECT * FROM sponsors WHERE id = ? AND event_id = ?",
        (sponsor_id, event_id),
    ).fetchone()

    if not sponsor:
        db.close()
        raise HTTPException(status_code=404, detail="Sponsor not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Prepare update values
    sponsor_name = sponsor_data.sponsor_name or sponsor["sponsor_name"]
    contact_person = sponsor_data.contact_person if sponsor_data.contact_person is not None else sponsor["contact_person"]
    contact_email = sponsor_data.contact_email if sponsor_data.contact_email is not None else sponsor["contact_email"]
    contact_phone = sponsor_data.contact_phone if sponsor_data.contact_phone is not None else sponsor["contact_phone"]
    sponsorship_amount = sponsor_data.sponsorship_amount if sponsor_data.sponsorship_amount is not None else sponsor["sponsorship_amount"]
    sponsorship_type = sponsor_data.sponsorship_type or sponsor["sponsorship_type"]
    status = sponsor_data.status or sponsor["status"]
    notes = sponsor_data.notes if sponsor_data.notes is not None else sponsor["notes"]

    # Validation
    if sponsorship_amount < 0:
        db.close()
        raise HTTPException(status_code=400, detail="Amount cannot be negative")

    if sponsorship_type not in SPONSORSHIP_TYPES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {', '.join(SPONSORSHIP_TYPES)}")

    if status not in SPONSOR_STATUSES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(SPONSOR_STATUSES)}")

    db.execute(
        """UPDATE sponsors SET sponsor_name = ?, contact_person = ?, contact_email = ?,
           contact_phone = ?, sponsorship_amount = ?, sponsorship_type = ?, status = ?,
           notes = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (sponsor_name, contact_person, contact_email, contact_phone, sponsorship_amount,
         sponsorship_type, status, notes, sponsor_id),
    )
    db.commit()
    db.close()

    return {
        "id": sponsor_id,
        "event_id": event_id,
        "sponsor_name": sponsor_name,
        "contact_person": contact_person,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "sponsorship_amount": sponsorship_amount,
        "sponsorship_type": sponsorship_type,
        "status": status,
        "notes": notes,
        "message": "Sponsor updated successfully"
    }


# ── Delete Sponsor ────────────────────────────────────────────────────────────

@router.delete("/{event_id}/sponsors/{sponsor_id}")
def delete_sponsor(
    event_id: int,
    sponsor_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Delete a sponsor"""
    db = get_db()

    sponsor = db.execute(
        "SELECT * FROM sponsors WHERE id = ? AND event_id = ?",
        (sponsor_id, event_id),
    ).fetchone()

    if not sponsor:
        db.close()
        raise HTTPException(status_code=404, detail="Sponsor not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    db.execute("DELETE FROM sponsors WHERE id = ?", (sponsor_id,))
    db.commit()
    db.close()

    return {"message": "Sponsor deleted successfully"}


# ── Get Sponsorship Summary ───────────────────────────────────────────────────

@router.get("/{event_id}/sponsors-summary")
def get_sponsorship_summary(
    event_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get sponsorship summary"""
    db = get_db()

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get summary by type
    by_type = db.execute(
        """SELECT sponsorship_type, COUNT(*) as count, SUM(sponsorship_amount) as total
           FROM sponsors WHERE event_id = ?
           GROUP BY sponsorship_type
           ORDER BY total DESC""",
        (event_id,),
    ).fetchall()

    # Get summary by status
    by_status = db.execute(
        """SELECT status, COUNT(*) as count, SUM(sponsorship_amount) as total
           FROM sponsors WHERE event_id = ?
           GROUP BY status
           ORDER BY total DESC""",
        (event_id,),
    ).fetchall()

    # Total confirmed sponsorship only
    confirmed_total = db.execute(
        """SELECT COALESCE(SUM(sponsorship_amount), 0) as total
           FROM sponsors WHERE event_id = ? AND status = 'confirmed'""",
        (event_id,),
    ).fetchone()

    # Total all sponsorship
    all_total = db.execute(
        """SELECT COALESCE(SUM(sponsorship_amount), 0) as total
           FROM sponsors WHERE event_id = ?""",
        (event_id,),
    ).fetchone()

    db.close()

    return {
        "event_id": event_id,
        "total_sponsorship_confirmed": confirmed_total["total"],
        "total_sponsorship_all": all_total["total"],
        "by_type": [dict(r) for r in by_type],
        "by_status": [dict(r) for r in by_status]
    }
