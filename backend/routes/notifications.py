from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import get_current_user

router = APIRouter()


@router.get("")
@router.get("/")
def get_notifications(current_user: dict = Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        """SELECT * FROM notifications
           WHERE user_id = ? OR LOWER(email) = LOWER(?)
           ORDER BY created_at DESC
           LIMIT 50""",
        (current_user["id"], current_user["email"]),
    ).fetchall()

    unread_count = db.execute(
        """SELECT COUNT(*) FROM notifications
           WHERE (user_id = ? OR LOWER(email) = LOWER(?)) AND is_read = 0""",
        (current_user["id"], current_user["email"]),
    ).fetchone()[0]
    db.close()

    return {
        "unread_count": unread_count,
        "notifications": [dict(r) for r in rows],
    }


@router.put("/{notification_id}/read")
def mark_as_read(notification_id: int, current_user: dict = Depends(get_current_user)):
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, email FROM notifications WHERE id = ?",
        (notification_id,),
    ).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Notification not found")

    if row["user_id"] != current_user["id"] and row["email"].lower() != current_user["email"].lower():
        db.close()
        raise HTTPException(status_code=403, detail="Unauthorized to modify this notification")

    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    db.commit()
    db.close()
    return {"message": "Notification marked as read"}


@router.put("/read-all")
def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        """UPDATE notifications SET is_read = 1
           WHERE user_id = ? OR LOWER(email) = LOWER(?)""",
        (current_user["id"], current_user["email"]),
    )
    db.commit()
    db.close()
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, current_user: dict = Depends(get_current_user)):
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, email FROM notifications WHERE id = ?",
        (notification_id,),
    ).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Notification not found")

    if row["user_id"] != current_user["id"] and row["email"].lower() != current_user["email"].lower():
        db.close()
        raise HTTPException(status_code=403, detail="Unauthorized")

    db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    db.commit()
    db.close()
    return {"message": "Notification deleted"}
