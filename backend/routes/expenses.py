from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db
from auth import require_roles, get_current_user

router = APIRouter()

EXPENSE_CATEGORIES = ["Venue", "Catering", "Marketing", "Equipment", "Staffing", "Transportation", "Logistics", "Other"]


class ExpenseIn(BaseModel):
    category: str = Field(..., description="Must be one of: Venue, Catering, Marketing, Equipment, Staffing, Transportation, Logistics, Other")
    description: str = Field(..., min_length=3)
    amount: float = Field(..., gt=0)
    date: str  # YYYY-MM-DD
    vendor_id: Optional[int] = None
    status: Optional[str] = "pending"  # pending, approved, rejected


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    vendor_id: Optional[int] = None
    status: Optional[str] = None


# ── Create Expense ─────────────────────────────────────────────────────────────

@router.post("/{event_id}/expenses", status_code=201)
def create_expense(
    event_id: int,
    expense_data: ExpenseIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Create an expense for an event"""
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

    # Validate category
    if expense_data.category not in EXPENSE_CATEGORIES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(EXPENSE_CATEGORIES)}")

    # Validate amount is positive
    if expense_data.amount <= 0:
        db.close()
        raise HTTPException(status_code=400, detail="Expense amount must be greater than 0")

    # Validate vendor if provided
    if expense_data.vendor_id:
        vendor = db.execute("SELECT id FROM vendors WHERE id = ?", (expense_data.vendor_id,)).fetchone()
        if not vendor:
            db.close()
            raise HTTPException(status_code=404, detail="Vendor not found")

    # Create expense
    cur = db.execute(
        """INSERT INTO expenses (event_id, category, description, amount, date, vendor_id, status, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_id, expense_data.category, expense_data.description, expense_data.amount,
         expense_data.date, expense_data.vendor_id, expense_data.status or "pending", current_user["id"]),
    )
    db.commit()
    expense_id = cur.lastrowid

    # Auto-create approval request for pending expenses
    if (expense_data.status or "pending") == "pending":
        db.execute(
            """INSERT INTO approvals (event_id, requester_id, request_type, reference_id, amount, reason, status)
               VALUES (?, ?, 'expense', ?, ?, ?, 'pending')""",
            (event_id, current_user["id"], expense_id, expense_data.amount, expense_data.description),
        )
        db.commit()

    db.close()

    return {
        "id": expense_id,
        "event_id": event_id,
        **expense_data.model_dump(),
        "message": "Expense created successfully"
    }


# ── Get Expenses for Event ─────────────────────────────────────────────────────

@router.get("/{event_id}/expenses")
def get_expenses(
    event_id: int,
    category: Optional[str] = None,
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    sort_by: Optional[str] = "date",
    order: Optional[str] = "desc",
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get all expenses for an event"""
    db = get_db()

    # Validate event exists
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization
    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    query = "SELECT * FROM expenses WHERE event_id = ?"
    params = [event_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    if status:
        query += " AND status = ?"
        params.append(status)

    if vendor_id:
        query += " AND vendor_id = ?"
        params.append(vendor_id)

    valid_sorts = {"date": "date", "amount": "amount", "category": "category", "created_at": "created_at"}
    sort_column = valid_sorts.get(sort_by, "date")
    sort_order = "DESC" if order and order.lower() == "desc" else "ASC"

    query += f" ORDER BY {sort_column} {sort_order}"

    rows = db.execute(query, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ── Get Single Expense ────────────────────────────────────────────────────────

@router.get("/expense/{expense_id}")
def get_expense(
    expense_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get a single expense"""
    db = get_db()

    expense = db.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not expense:
        db.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    # Authorization
    if current_user and current_user["role"] != "admin":
        event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (expense["event_id"],)).fetchone()
        if event["organizer_id"] != current_user["id"]:
            db.close()
            raise HTTPException(status_code=403, detail="Not authorized")

    db.close()
    return dict(expense)


# ── Update Expense ─────────────────────────────────────────────────────────────

@router.put("/{event_id}/expenses/{expense_id}")
def update_expense(
    event_id: int,
    expense_id: int,
    expense_data: ExpenseUpdate,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Update an expense"""
    db = get_db()

    expense = db.execute(
        "SELECT * FROM expenses WHERE id = ? AND event_id = ?",
        (expense_id, event_id),
    ).fetchone()

    if not expense:
        db.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Prepare update values
    category = expense_data.category or expense["category"]
    description = expense_data.description or expense["description"]
    amount = expense_data.amount or expense["amount"]
    date = expense_data.date or expense["date"]
    vendor_id = expense_data.vendor_id if expense_data.vendor_id is not None else expense["vendor_id"]
    status = expense_data.status or expense["status"]

    # Validate
    if amount <= 0:
        db.close()
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    if category not in EXPENSE_CATEGORIES:
        db.close()
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(EXPENSE_CATEGORIES)}")

    db.execute(
        """UPDATE expenses SET category = ?, description = ?, amount = ?, date = ?,
           vendor_id = ?, status = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (category, description, amount, date, vendor_id, status, expense_id),
    )
    db.commit()
    db.close()

    return {
        "id": expense_id,
        "event_id": event_id,
        "category": category,
        "description": description,
        "amount": amount,
        "date": date,
        "vendor_id": vendor_id,
        "status": status,
        "message": "Expense updated successfully"
    }


# ── Delete Expense ────────────────────────────────────────────────────────────

@router.delete("/{event_id}/expenses/{expense_id}")
def delete_expense(
    event_id: int,
    expense_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    """Delete an expense"""
    db = get_db()

    expense = db.execute(
        "SELECT * FROM expenses WHERE id = ? AND event_id = ?",
        (expense_id, event_id),
    ).fetchone()

    if not expense:
        db.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    db.close()

    return {"message": "Expense deleted successfully"}


# ── Get Expense Summary ────────────────────────────────────────────────────────

@router.get("/{event_id}/expenses-summary")
def get_expenses_summary(
    event_id: int,
    current_user: Optional[dict] = Depends(require_roles(["admin", "organizer"], auto_error=False)),
):
    """Get expense summary by category"""
    db = get_db()

    # Authorization
    event = db.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user and current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get summary by category
    rows = db.execute(
        """SELECT category, COUNT(*) as count, SUM(amount) as total
           FROM expenses WHERE event_id = ?
           GROUP BY category
           ORDER BY total DESC""",
        (event_id,),
    ).fetchall()

    # Total expenses
    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    db.close()

    return {
        "event_id": event_id,
        "total_expenses": total["total"],
        "by_category": [dict(r) for r in rows]
    }
