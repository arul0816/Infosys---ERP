from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database import get_db
from auth import require_roles
from ops import find_resource_conflict, write_audit

router = APIRouter()


class ResourceIn(BaseModel):
    name: str = Field(..., min_length=2)
    quantity: int = Field(..., ge=1)


class AllocateIn(BaseModel):
    event_id: int
    resource_id: int
    quantity_used: int = Field(..., ge=1)


@router.post("", status_code=201)
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
    rid = cur.lastrowid
    write_audit(
        db,
        actor=current_user,
        action="resource.create",
        object_type="resource",
        object_id=rid,
        object_label=res.name.strip(),
        new_value={"name": res.name.strip(), "quantity": res.quantity},
    )
    db.commit()
    db.close()
    return {"id": rid, **res.model_dump(), "status": "available"}


@router.get("")
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

    event = db.execute("SELECT * FROM events WHERE id = ?", (alloc.event_id,)).fetchone()
    if not event:
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user["role"] != "admin" and event["organizer_id"] != current_user["id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only allocate resources to your own events.")

    if event["status"] in ["cancelled", "draft"]:
        db.close()
        raise HTTPException(status_code=400, detail=f"Cannot allocate resources to a {event['status']} event.")

    resource = db.execute(
        "SELECT * FROM resources WHERE id = ?", (alloc.resource_id,)
    ).fetchone()
    if not resource:
        db.close()
        raise HTTPException(status_code=404, detail="Resource not found")

    # Time-window conflict detection allowing sequential reuse
    conflict_event, overlapping_qty = find_resource_conflict(
        db,
        alloc.resource_id,
        dict(event),
        alloc.quantity_used,
        resource["quantity"],
    )
    if conflict_event:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=(
                f"Resource conflict: '{resource['name']}' has {resource['quantity']} total units, but "
                f"{overlapping_qty + alloc.quantity_used} units are needed during overlapping event "
                f"'{conflict_event['name']}' on {conflict_event['date']} "
                f"({conflict_event['time']}–{conflict_event.get('end_time') or 'end'})."
            ),
        )

    cur = db.execute(
        "INSERT INTO event_resources (event_id, resource_id, quantity_used) VALUES (?, ?, ?)",
        (alloc.event_id, alloc.resource_id, alloc.quantity_used),
    )
    alloc_id = cur.lastrowid

    write_audit(
        db,
        actor=current_user,
        action="resource.allocate",
        object_type="resource",
        object_id=alloc.resource_id,
        object_label=f"{resource['name']} -> {event['name']}",
        new_value={"allocation_id": alloc_id, "event_id": alloc.event_id, "quantity_used": alloc.quantity_used},
    )

    db.commit()
    db.close()
    return {"message": "Resource allocated successfully", "allocation_id": alloc_id}


@router.get("/allocations")
def get_allocations():
    db = get_db()
    rows = db.execute("""
        SELECT er.id, er.event_id, er.resource_id, e.name AS event_name, e.date AS event_date,
               e.time AS event_time, e.end_time AS event_end_time, r.name AS resource_name,
               r.quantity AS total_resource_quantity, er.quantity_used
        FROM event_resources er
        JOIN events e ON er.event_id = e.id
        JOIN resources r ON er.resource_id = r.id
        ORDER BY e.date DESC, e.time ASC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.delete("/allocations/{allocation_id}")
def deallocate_resource(
    allocation_id: int,
    current_user: dict = Depends(require_roles(["admin", "organizer"])),
):
    db = get_db()
    alloc = db.execute("SELECT er.*, r.name AS resource_name FROM event_resources er JOIN resources r ON er.resource_id = r.id WHERE er.id = ?", (allocation_id,)).fetchone()
    if not alloc:
        db.close()
        raise HTTPException(status_code=404, detail="Allocation not found")

    db.execute("DELETE FROM event_resources WHERE id = ?", (allocation_id,))
    write_audit(
        db,
        actor=current_user,
        action="resource.deallocate",
        object_type="resource",
        object_id=alloc["resource_id"],
        object_label=alloc["resource_name"],
        previous_value={"event_id": alloc["event_id"], "quantity_used": alloc["quantity_used"]},
        new_value=None,
    )
    db.commit()
    db.close()
    return {"message": "Resource released back to inventory"}


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    db = get_db()
    row = db.execute("SELECT id, name FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Resource not found")

    write_audit(
        db,
        actor=current_user,
        action="resource.delete",
        object_type="resource",
        object_id=resource_id,
        object_label=row["name"],
        previous_value=None,
        new_value=None,
    )
    db.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    db.commit()
    db.close()
    return {"message": "Resource deleted"}
