from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from auth import require_roles, get_current_user

router = APIRouter()


class BudgetIn(BaseModel):
    total_budget: float = Field(..., ge=0.0)
    notes: Optional[str] = ""


class BudgetSummaryOut(BaseModel):
    event_id: int
    total_budget: float
    total_expenses: float
    total_sponsorship: float
    remaining_budget: float
    budget_utilization: float  # percentage


# ── Create Budget ──────────────────────────────────────────────────────────────

@router.post("/{event_id}", status_code=201)
def create_budget(
    event_id: int,
    budget_data: BudgetIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Create budget for an event"""
    db = get_db()

    # Check event exists
    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Check authorization
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized to manage this event")

    # Check if budget already exists
    existing = db.execute("SELECT id FROM budgets WHERE event_id = ?", (event_id,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(status_code=409, detail="Budget already exists for this event")

    # Create budget
    cur = db.execute(
        """INSERT INTO budgets (event_id, total_budget, notes, created_by)
           VALUES (?, ?, ?, ?)""",
        (event_id, budget_data.total_budget, budget_data.notes, current_user["id"]),
    )
    db.commit()
    budget_id = cur.lastrowid
    db.close()

    return {
        "id": budget_id,
        "event_id": event_id,
        "total_budget": budget_data.total_budget,
        "notes": budget_data.notes,
        "message": "Budget created successfully"
    }


# ── Get Budget ─────────────────────────────────────────────────────────────────

@router.get("/{event_id}")
def get_budget(
    event_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get budget for an event"""
    db = get_db()

    budget = db.execute(
        "SELECT * FROM budgets WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if not budget:
        db.close()
        raise HTTPException(status_code=404, detail="Budget not found for this event")

    # Authorization check
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    db.close()
    return dict(budget)


# ── Update Budget ──────────────────────────────────────────────────────────────

@router.put("/{event_id}")
def update_budget(
    event_id: int,
    budget_data: BudgetIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Update budget for an event"""
    db = get_db()

    budget = db.execute(
        "SELECT * FROM budgets WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if not budget:
        db.close()
        raise HTTPException(status_code=404, detail="Budget not found")

    # Check authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    db.execute(
        """UPDATE budgets SET total_budget = ?, notes = ?, updated_at = datetime('now')
           WHERE event_id = ?""",
        (budget_data.total_budget, budget_data.notes, event_id),
    )
    db.commit()
    db.close()

    return {
        "event_id": event_id,
        "total_budget": budget_data.total_budget,
        "notes": budget_data.notes,
        "message": "Budget updated successfully"
    }


# ── Delete Budget ──────────────────────────────────────────────────────────────

@router.delete("/{event_id}")
def delete_budget(
    event_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    """Delete budget for an event (Admin only)"""
    db = get_db()

    budget = db.execute(
        "SELECT * FROM budgets WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if not budget:
        db.close()
        raise HTTPException(status_code=404, detail="Budget not found")

    db.execute("DELETE FROM budgets WHERE event_id = ?", (event_id,))
    db.commit()
    db.close()

    return {"message": "Budget deleted successfully"}


# ── Get Budget Summary with Calculations ───────────────────────────────────────

@router.get("/{event_id}/summary")
def get_budget_summary(
    event_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get budget summary with expenses and utilization"""
    db = get_db()

    budget = db.execute(
        "SELECT * FROM budgets WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if not budget:
        db.close()
        raise HTTPException(status_code=404, detail="Budget not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Calculate total expenses (approved only)
    expenses_result = db.execute(
        """SELECT COALESCE(SUM(amount), 0) as total
           FROM expenses WHERE event_id = ? AND status IN ('approved', 'pending')""",
        (event_id,),
    ).fetchone()
    total_expenses = expenses_result["total"]

    # Calculate total sponsorship (confirmed only)
    sponsorship_result = db.execute(
        """SELECT COALESCE(SUM(sponsorship_amount), 0) as total
           FROM sponsors WHERE event_id = ? AND status = 'confirmed'""",
        (event_id,),
    ).fetchone()
    total_sponsorship = sponsorship_result["total"]

    total_budget = budget["total_budget"]
    remaining_budget = total_budget - total_expenses

    # Handle division by zero
    budget_utilization = (total_expenses / total_budget * 100) if total_budget > 0 else 0

    db.close()

    return {
        "event_id": event_id,
        "total_budget": total_budget,
        "total_expenses": total_expenses,
        "total_sponsorship": total_sponsorship,
        "remaining_budget": remaining_budget,
        "budget_utilization": round(budget_utilization, 2),
        "is_over_budget": remaining_budget < 0
    }
