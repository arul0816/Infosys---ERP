from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database import get_db
from auth import require_roles

router = APIRouter()


class VenueIn(BaseModel):
    name: str = Field(..., min_length=2)
    capacity: int = Field(..., ge=1)
    location: str = Field(..., min_length=2)


@router.post("/", status_code=201)
def add_venue(
    venue: VenueIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    cur = db.execute(
        "INSERT INTO venues (name, capacity, location) VALUES (?, ?, ?)",
        (venue.name.strip(), venue.capacity, venue.location.strip()),
    )
    db.commit()
    venue_id = cur.lastrowid
    db.close()
    return {"id": venue_id, **venue.model_dump(), "availability": True}


@router.get("/")
def get_venues():
    db = get_db()
    rows = db.execute("SELECT * FROM venues ORDER BY name").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.delete("/{venue_id}")
def delete_venue(
    venue_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    db = get_db()
    row = db.execute("SELECT id FROM venues WHERE id = ?", (venue_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Venue not found")

    # Check if venue is currently assigned to upcoming events
    active_event = db.execute(
        "SELECT id, name FROM events WHERE venue_id = ? AND status != 'cancelled'",
        (venue_id,),
    ).fetchone()
    if active_event:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete venue: it is assigned to event '{active_event['name']}'.",
        )

    db.execute("DELETE FROM venues WHERE id = ?", (venue_id,))
    db.commit()
    db.close()
    return {"message": "Venue deleted"}
