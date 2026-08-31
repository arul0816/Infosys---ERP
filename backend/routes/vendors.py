from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from auth import require_roles

router = APIRouter()


class VendorIn(BaseModel):
    name: str = Field(..., min_length=2)
    service_type: str
    contact: str = Field(..., min_length=5)
    email: Optional[str] = ""


class AssignIn(BaseModel):
    vendor_id: int
    event_id: int


class RatingIn(BaseModel):
    rating: float = Field(..., ge=0, le=5)


# ── Vendor CRUD ───────────────────────────────────────────────────────────────

@router.post("", status_code=201)
@router.post("/", status_code=201)
def add_vendor(
    v: VendorIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    cur = db.execute(
        "INSERT INTO vendors (name, service_type, contact, email) VALUES (?, ?, ?, ?)",
        (v.name.strip(), v.service_type, v.contact.strip(), v.email.strip() if v.email else ""),
    )
    db.commit()
    vid = cur.lastrowid
    db.close()
    return {"id": vid, **v.model_dump(), "rating": 0.0}


@router.get("")
@router.get("/")
def get_vendors():
    db = get_db()
    rows = db.execute("SELECT * FROM vendors ORDER BY name").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.put("/{vendor_id}/rating")
def rate_vendor(
    vendor_id: int,
    body: RatingIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute("SELECT id FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")

    db.execute("UPDATE vendors SET rating = ? WHERE id = ?", (body.rating, vendor_id))
    db.commit()
    db.close()
    return {"message": "Rating updated successfully"}


@router.delete("/{vendor_id}")
def delete_vendor(
    vendor_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    db = get_db()
    row = db.execute("SELECT id FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
    db.commit()
    db.close()
    return {"message": "Vendor deleted"}


# ── Vendor Assignments ────────────────────────────────────────────────────────

@router.get("/assignments")
def get_all_assignments():
    db = get_db()
    rows = db.execute("""
        SELECT va.id, v.name AS vendor_name, v.service_type, v.contact AS vendor_contact,
               e.name AS event_name, va.event_id, va.vendor_id
        FROM vendor_assignments va
        JOIN vendors v ON va.vendor_id = v.id
        JOIN events  e ON va.event_id  = e.id
        ORDER BY e.name
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("/assign", status_code=201)
def assign_vendor(
    body: AssignIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()

    vendor = db.execute("SELECT id FROM vendors WHERE id = ?", (body.vendor_id,)).fetchone()
    if not vendor:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")

    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (body.event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only assign vendors to your own events.")

    # Duplicate assignment check
    dup = db.execute(
        "SELECT id FROM vendor_assignments WHERE vendor_id = ? AND event_id = ?",
        (body.vendor_id, body.event_id),
    ).fetchone()
    if dup:
        db.close()
        raise HTTPException(status_code=400, detail="Vendor is already assigned to this event.")

    cur = db.execute(
        "INSERT INTO vendor_assignments (vendor_id, event_id) VALUES (?, ?)",
        (body.vendor_id, body.event_id),
    )
    db.commit()
    aid = cur.lastrowid
    db.close()
    return {"id": aid, "message": "Vendor assigned successfully"}


@router.delete("/assignments/{assignment_id}")
def remove_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    row = db.execute(
        """SELECT va.id, va.event_id, e.organizer_id
           FROM vendor_assignments va
           JOIN events e ON va.event_id = e.id
           WHERE va.id = ?""",
        (assignment_id,),
    ).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user["role"] != "admin" and row["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only remove vendor assignments from your own events.")

    db.execute("DELETE FROM vendor_assignments WHERE id = ?", (assignment_id,))
    db.commit()
    db.close()
    return {"message": "Vendor assignment removed"}
