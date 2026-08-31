from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from auth import require_roles, get_current_user

router = APIRouter()

RATING_MIN = 1
RATING_MAX = 5


class VendorPerformanceIn(BaseModel):
    quality_rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)
    timeliness_rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)
    cost_rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)
    communication_rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)
    overall_rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)
    comments: Optional[str] = ""


class VendorPerformanceUpdate(BaseModel):
    quality_rating: Optional[int] = None
    timeliness_rating: Optional[int] = None
    cost_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    overall_rating: Optional[int] = None
    comments: Optional[str] = None


# ── Submit Vendor Rating ───────────────────────────────────────────────────────

@router.post("/{vendor_id}/performance", status_code=201)
def submit_vendor_rating(
    vendor_id: int,
    event_id: int = Query(..., description="Event ID"),
    performance_data: VendorPerformanceIn = None,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Submit a performance rating for a vendor after an event"""
    db = get_db()

    # Validate vendor exists
    vendor = db.execute("SELECT id FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if not vendor:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Validate event exists
    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized to rate vendors for this event")

    # Check if vendor was assigned to this event
    assignment = db.execute(
        "SELECT id FROM vendor_assignments WHERE vendor_id = ? AND event_id = ?",
        (vendor_id, event_id),
    ).fetchone()

    if not assignment:
        db.close()
        raise HTTPException(status_code=400, detail="This vendor was not assigned to this event")

    # Check if rating already exists (allow update)
    existing_rating = db.execute(
        "SELECT id FROM vendor_performance WHERE vendor_id = ? AND event_id = ?",
        (vendor_id, event_id),
    ).fetchone()

    if existing_rating:
        db.close()
        raise HTTPException(status_code=409, detail="Rating already submitted for this vendor/event combination")

    # Validate ratings
    ratings_dict = performance_data.model_dump()
    for key, value in ratings_dict.items():
        if key != "comments" and value is not None:
            if not (RATING_MIN <= value <= RATING_MAX):
                db.close()
                raise HTTPException(status_code=400, detail=f"{key} must be between {RATING_MIN} and {RATING_MAX}")

    # Create rating
    cur = db.execute(
        """INSERT INTO vendor_performance (vendor_id, event_id, quality_rating, timeliness_rating,
                                           cost_rating, communication_rating, overall_rating, comments, rated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (vendor_id, event_id, performance_data.quality_rating, performance_data.timeliness_rating,
         performance_data.cost_rating, performance_data.communication_rating,
         performance_data.overall_rating, performance_data.comments, current_user["id"]),
    )
    db.commit()
    rating_id = cur.lastrowid
    db.close()

    return {
        "id": rating_id,
        "vendor_id": vendor_id,
        "event_id": event_id,
        **performance_data.model_dump(),
        "message": "Vendor rating submitted successfully"
    }


# ── Get Vendor Ratings for Event ───────────────────────────────────────────────

@router.get("/{vendor_id}/performance")
def get_vendor_performance_ratings(
    vendor_id: int,
    event_id: Optional[int] = None,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get performance ratings for a vendor"""
    db = get_db()

    # Validate vendor exists
    vendor = db.execute("SELECT id FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if not vendor:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")

    query = "SELECT * FROM vendor_performance WHERE vendor_id = ?"
    params = [vendor_id]

    if event_id:
        query += " AND event_id = ?"
        params.append(event_id)

    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Get Vendor Performance Summary ────────────────────────────────────────────

@router.get("/{vendor_id}/performance-summary")
def get_vendor_performance_summary(
    vendor_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get average performance ratings for a vendor across all events"""
    db = get_db()

    # Validate vendor exists
    vendor = db.execute("SELECT id, name FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if not vendor:
        db.close()
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Get all ratings and calculate averages
    summary = db.execute(
        """SELECT
               COUNT(*) as total_ratings,
               ROUND(AVG(quality_rating), 2) as avg_quality,
               ROUND(AVG(timeliness_rating), 2) as avg_timeliness,
               ROUND(AVG(cost_rating), 2) as avg_cost,
               ROUND(AVG(communication_rating), 2) as avg_communication,
               ROUND(AVG(overall_rating), 2) as avg_overall
           FROM vendor_performance
           WHERE vendor_id = ?""",
        (vendor_id,),
    ).fetchone()

    # Get rating distribution
    distribution = db.execute(
        """SELECT overall_rating, COUNT(*) as count
           FROM vendor_performance WHERE vendor_id = ?
           GROUP BY overall_rating
           ORDER BY overall_rating DESC""",
        (vendor_id,),
    ).fetchall()

    # Get recent ratings
    recent = db.execute(
        """SELECT vp.*, e.name as event_name FROM vendor_performance vp
           JOIN events e ON vp.event_id = e.id
           WHERE vp.vendor_id = ?
           ORDER BY vp.created_at DESC
           LIMIT 5""",
        (vendor_id,),
    ).fetchall()

    db.close()

    summary_dict = dict(summary) if summary else {}

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "summary": {
            "total_ratings": summary_dict.get("total_ratings", 0),
            "avg_quality": summary_dict.get("avg_quality", 0),
            "avg_timeliness": summary_dict.get("avg_timeliness", 0),
            "avg_cost": summary_dict.get("avg_cost", 0),
            "avg_communication": summary_dict.get("avg_communication", 0),
            "avg_overall": summary_dict.get("avg_overall", 0),
        },
        "distribution": [dict(r) for r in distribution],
        "recent_ratings": [dict(r) for r in recent]
    }


# ── Top Vendors by Rating ──────────────────────────────────────────────────────

@router.get("/rankings/top-vendors")
def get_top_vendors(
    limit: int = Query(10, ge=1, le=100),
    min_ratings: int = Query(1, ge=1),
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get top-rated vendors"""
    db = get_db()

    rows = db.execute(
        """SELECT v.id, v.name, v.service_type,
                  COUNT(vp.id) as total_ratings,
                  ROUND(AVG(vp.overall_rating), 2) as avg_rating,
                  ROUND(AVG(vp.quality_rating), 2) as quality,
                  ROUND(AVG(vp.timeliness_rating), 2) as timeliness,
                  ROUND(AVG(vp.cost_rating), 2) as cost,
                  ROUND(AVG(vp.communication_rating), 2) as communication
           FROM vendors v
           LEFT JOIN vendor_performance vp ON v.id = vp.vendor_id
           GROUP BY v.id
           HAVING COUNT(vp.id) >= ?
           ORDER BY avg_rating DESC
           LIMIT ?""",
        (min_ratings, limit),
    ).fetchall()

    db.close()

    return [dict(r) for r in rows]


# ── Update Vendor Performance Rating ───────────────────────────────────────────

@router.put("/{vendor_id}/performance/{performance_id}")
def update_vendor_rating(
    vendor_id: int,
    performance_id: int,
    performance_data: VendorPerformanceUpdate,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Update a vendor performance rating"""
    db = get_db()

    performance = db.execute(
        "SELECT * FROM vendor_performance WHERE id = ? AND vendor_id = ?",
        (performance_id, vendor_id),
    ).fetchone()

    if not performance:
        db.close()
        raise HTTPException(status_code=404, detail="Performance rating not found")

    # Authorization - only the person who rated can update
    if current_user["role"] != "admin" and performance["rated_by"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized to update this rating")

    # Prepare values
    quality = performance_data.quality_rating or performance["quality_rating"]
    timeliness = performance_data.timeliness_rating or performance["timeliness_rating"]
    cost = performance_data.cost_rating or performance["cost_rating"]
    communication = performance_data.communication_rating or performance["communication_rating"]
    overall = performance_data.overall_rating or performance["overall_rating"]
    comments = performance_data.comments if performance_data.comments is not None else performance["comments"]

    # Validate
    for rating in [quality, timeliness, cost, communication, overall]:
        if not (RATING_MIN <= rating <= RATING_MAX):
            db.close()
            raise HTTPException(status_code=400, detail=f"Ratings must be between {RATING_MIN} and {RATING_MAX}")

    db.execute(
        """UPDATE vendor_performance SET quality_rating = ?, timeliness_rating = ?,
           cost_rating = ?, communication_rating = ?, overall_rating = ?, comments = ?,
           updated_at = datetime('now')
           WHERE id = ?""",
        (quality, timeliness, cost, communication, overall, comments, performance_id),
    )
    db.commit()
    db.close()

    return {
        "id": performance_id,
        "vendor_id": vendor_id,
        "quality_rating": quality,
        "timeliness_rating": timeliness,
        "cost_rating": cost,
        "communication_rating": communication,
        "overall_rating": overall,
        "comments": comments,
        "message": "Rating updated successfully"
    }
