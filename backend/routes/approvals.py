from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from auth import require_roles, get_current_user

router = APIRouter()

REQUEST_TYPES = ["vendor", "expense", "resource", "sponsorship"]
APPROVAL_STATUSES = ["pending", "approved", "rejected"]


class ApprovalIn(BaseModel):
    event_id: int
    request_type: str  # 'vendor', 'expense', 'resource', 'sponsorship'
    reference_id: int
    amount: Optional[float] = 0
    reason: Optional[str] = ""


class ApprovalReviewIn(BaseModel):
    status: str  # 'approved', 'rejected'
    reviewer_comment: Optional[str] = ""


# ── Create Approval Request ───────────────────────────────────────────────────

@router.post("")
@router.post("/", status_code=201)
def create_approval(
    approval_data: ApprovalIn,
    current_user: dict = Depends(get_current_user),
):
    """Submit an approval request"""
    db = get_db()

    # Validate event exists
    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (approval_data.event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate request type
    if approval_data.request_type not in REQUEST_TYPES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid request type. Must be one of: {', '.join(REQUEST_TYPES)}")

    # Validate reference exists based on request type
    if approval_data.request_type == "vendor":
        ref = db.execute("SELECT id FROM vendors WHERE id = ?", (approval_data.reference_id,)).fetchone()
    elif approval_data.request_type == "expense":
        ref = db.execute("SELECT id FROM expenses WHERE id = ?", (approval_data.reference_id,)).fetchone()
    elif approval_data.request_type == "resource":
        ref = db.execute("SELECT id FROM resources WHERE id = ?", (approval_data.reference_id,)).fetchone()
    elif approval_data.request_type == "sponsorship":
        ref = db.execute("SELECT id FROM sponsors WHERE id = ?", (approval_data.reference_id,)).fetchone()

    if not ref:
        db.close()
        raise HTTPException(status_code=404, detail=f"{approval_data.request_type.capitalize()} not found")

    # Create approval request
    cur = db.execute(
        """INSERT INTO approvals (event_id, requester_id, request_type, reference_id, amount, reason, status)
           VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
        (approval_data.event_id, current_user["id"], approval_data.request_type,
         approval_data.reference_id, approval_data.amount or 0, approval_data.reason),
    )
    db.commit()
    approval_id = cur.lastrowid

    # Send notification
    event_name = db.execute("SELECT name FROM events WHERE id = ?", (approval_data.event_id,)).fetchone()["name"]
    db.execute(
        """INSERT INTO notifications (user_id, event_id, title, message, type)
           VALUES (?, ?, ?, ?, 'approval')""",
        (current_user["id"], approval_data.event_id, "✋ Approval Request Submitted",
         f"Your {approval_data.request_type} approval request for '{event_name}' has been submitted for review."),
    )
    db.commit()
    db.close()

    return {
        "id": approval_id,
        "event_id": approval_data.event_id,
        "status": "pending",
        **approval_data.model_dump(),
        "message": "Approval request submitted successfully"
    }


# ── Get All Approvals ────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def get_approvals(
    event_id: Optional[int] = None,
    status: Optional[str] = None,
    request_type: Optional[str] = None,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Get all approval requests"""
    db = get_db()

    query = "SELECT * FROM approvals WHERE 1=1"
    params = []

    # Non-admin can only see approvals for their events
    if current_user["role"] != "admin":
        query += """
            AND event_id IN (
                SELECT id FROM events WHERE organizer_id = ?
            )
        """
        params.append(current_user["id"])

    if event_id:
        query += " AND event_id = ?"
        params.append(event_id)

    if status:
        query += " AND status = ?"
        params.append(status)

    if request_type:
        query += " AND request_type = ?"
        params.append(request_type)

    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Get Single Approval ───────────────────────────────────────────────────────

@router.get("/{approval_id}")
def get_approval(
    approval_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Get a single approval request"""
    db = get_db()

    approval = db.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
    if not approval:
        db.close()
        raise HTTPException(status_code=404, detail="Approval not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (approval["event_id"],)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    db.close()
    return dict(approval)


# ── Review Approval Request ───────────────────────────────────────────────────

@router.put("/{approval_id}/review")
def review_approval(
    approval_id: int,
    review_data: ApprovalReviewIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Approve or reject an approval request"""
    db = get_db()

    approval = db.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
    if not approval:
        db.close()
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval["status"] != "pending":
        db.close()
        raise HTTPException(status_code=400, detail="Approval request has already been reviewed")

    # Authorization
    event = db.execute("SELECT organizer_id, name FROM events WHERE id = ?", (approval["event_id"],)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized to review approvals for this event")

    # Validate review status
    if review_data.status not in ["approved", "rejected"]:
        db.close()
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    # Update approval
    db.execute(
        """UPDATE approvals SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), 
           reviewer_comment = ? WHERE id = ?""",
        (review_data.status, current_user["id"], review_data.reviewer_comment, approval_id),
    )

    # Sync linked entity status
    ref_status = "approved" if review_data.status == "approved" else "rejected"
    if approval["request_type"] == "expense":
        db.execute("UPDATE expenses SET status = ?, updated_at = datetime('now') WHERE id = ?", (ref_status, approval["reference_id"]))
    elif approval["request_type"] == "sponsorship":
        sponsor_status = "confirmed" if review_data.status == "approved" else "rejected"
        db.execute("UPDATE sponsors SET status = ?, updated_at = datetime('now') WHERE id = ?", (sponsor_status, approval["reference_id"]))

    # Get requester info
    requester = db.execute("SELECT id, name, email FROM users WHERE id = ?", (approval["requester_id"],)).fetchone()

    # Send notification to requester
    if review_data.status == "approved":
        title = f"✅ Approval Accepted"
        message = f"Your {approval['request_type']} approval request for '{event['name']}' has been APPROVED."
    else:
        title = f"❌ Approval Rejected"
        message = f"Your {approval['request_type']} approval request for '{event['name']}' has been REJECTED."
        if review_data.reviewer_comment:
            message += f" Reason: {review_data.reviewer_comment}"

    db.execute(
        """INSERT INTO notifications (user_id, email, event_id, title, message, type)
           VALUES (?, ?, ?, ?, ?, 'approval')""",
        (approval["requester_id"], requester["email"], approval["event_id"], title, message),
    )

    db.commit()
    db.close()

    return {
        "id": approval_id,
        "status": review_data.status,
        "reviewed_by": current_user["id"],
        "reviewer_comment": review_data.reviewer_comment,
        "message": f"Approval request {review_data.status} successfully"
    }


# ── Get My Approval Requests ──────────────────────────────────────────────────

@router.get("/user/my-requests")
def get_my_approvals(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Get current user's approval requests"""
    db = get_db()

    query = "SELECT * FROM approvals WHERE requester_id = ?"
    params = [current_user["id"]]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Get Pending Approvals Count ───────────────────────────────────────────────

@router.get("/stats/pending-count")
def get_pending_approvals_count(
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Get count of pending approvals"""
    db = get_db()

    query = """SELECT COUNT(*) as count FROM approvals WHERE status = 'pending'"""
    params = []

    if current_user["role"] != "admin":
        query += """ AND event_id IN (SELECT id FROM events WHERE organizer_id = ?)"""
        params.append(current_user["id"])

    result = db.execute(query, params).fetchone()
    db.close()

    return {"pending_count": result["count"]}
