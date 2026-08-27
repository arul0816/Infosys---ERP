from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database import get_db
from auth import require_roles

router = APIRouter()


class ResourceIn(BaseModel):
    name: str = Field(..., min_length=2)
    quantity: int = Field(..., ge=1)


class AllocateIn(BaseModel):
    event_id: int
    resource_id: int
    quantity_used: int = Field(..., ge=1)


@router.post("/", status_code=201)
def add_resource(
    res: ResourceIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    cur = db.execute(
        "INSERT INTO resources (name, quantity) VALUES (?, ?)",
        (res.name.strip(), res.quantity),
    )
    db.commit()
    rid = cur.lastrowid
    db.close()
    return {"id": rid, **res.model_dump(), "status": "available"}


@router.get("/")
def get_resources():
    db = get_db()
    rows = db.execute("SELECT * FROM resources ORDER BY name").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("/allocate", status_code=201)
def allocate_resource(
    alloc: AllocateIn,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()

    event = db.execute("SELECT id, organizer_id FROM events WHERE id = ?", (alloc.event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only allocate resources to your own events.")

    resource = db.execute(
        "SELECT * FROM resources WHERE id = ?", (alloc.resource_id,)
    ).fetchone()
    if not resource:
        db.close()
        raise HTTPException(status_code=404, detail="Resource not found")

    if resource["quantity"] < alloc.quantity_used:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Only {resource['quantity']} units available for '{resource['name']}'",
        )

    db.execute(
        "INSERT INTO event_resources (event_id, resource_id, quantity_used) VALUES (?, ?, ?)",
        (alloc.event_id, alloc.resource_id, alloc.quantity_used),
    )
    db.execute(
        "UPDATE resources SET quantity = quantity - ? WHERE id = ?",
        (alloc.quantity_used, alloc.resource_id),
    )
    db.commit()
    db.close()
    return {"message": "Resource allocated successfully"}


@router.get("/allocations")
def get_allocations():
    db = get_db()
    rows = db.execute("""
        SELECT er.id, er.event_id, er.resource_id, e.name AS event_name, r.name AS resource_name, er.quantity_used
        FROM event_resources er
        JOIN events e ON er.event_id = e.id
        JOIN resources r ON er.resource_id = r.id
        ORDER BY e.name
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.delete("/allocations/{allocation_id}")
def deallocate_resource(
    allocation_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    alloc = db.execute("SELECT * FROM event_resources WHERE id = ?", (allocation_id,)).fetchone()
    if not alloc:
        db.close()
        raise HTTPException(status_code=404, detail="Allocation not found")

    # Restore resource quantity
    db.execute(
        "UPDATE resources SET quantity = quantity + ? WHERE id = ?",
        (alloc["quantity_used"], alloc["resource_id"]),
    )
    db.execute("DELETE FROM event_resources WHERE id = ?", (allocation_id,))
    db.commit()
    db.close()
    return {"message": "Resource returned to inventory"}


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    db = get_db()
    row = db.execute("SELECT id FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Resource not found")
    db.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    db.commit()
    db.close()
    return {"message": "Resource deleted"}
