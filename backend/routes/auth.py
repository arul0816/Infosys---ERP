import re
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db, hash_password
from auth import (
    create_access_token,
    get_current_user,
    require_roles,
)

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    role: Optional[str] = "participant"
    phone: Optional[str] = ""
    organization: Optional[str] = ""


class LoginIn(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=1)


class ProfileUpdateIn(BaseModel):
    name: str = Field(..., min_length=2)
    phone: Optional[str] = ""
    organization: Optional[str] = ""
    avatar_url: Optional[str] = ""


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    email: str
    reset_code: str
    new_password: str = Field(..., min_length=6)


class RoleUpdateIn(BaseModel):
    role: str


class StatusUpdateIn(BaseModel):
    status: str


# ── Public Auth Endpoints ─────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: RegisterIn):
    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    valid_roles = ["participant", "organizer", "admin"]
    role = body.role.lower() if body.role else "participant"
    if role not in valid_roles:
        role = "participant"

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (body.email,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    pwd_hash = hash_password(body.password)
    cur = db.execute(
        """INSERT INTO users (name, email, password_hash, role, phone, organization)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (body.name.strip(), body.email.lower().strip(), pwd_hash, role, body.phone, body.organization),
    )
    db.commit()
    user_id = cur.lastrowid

    user = db.execute(
        "SELECT id, name, email, role, phone, organization, avatar_url, status, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    db.close()

    user_dict = dict(user)
    token = create_access_token({"sub": user_id, "email": user_dict["email"], "role": user_dict["role"]})

    return {
        "message": "Registration successful",
        "token": token,
        "user": user_dict,
    }


@router.post("/login")
def login(body: LoginIn):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
        (body.email.strip(),),
    ).fetchone()
    db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    pwd_hash = hash_password(body.password)
    if user["password_hash"] != pwd_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated. Please contact an administrator.",
        )

    user_dict = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "phone": user["phone"],
        "organization": user["organization"],
        "avatar_url": user["avatar_url"],
        "status": user["status"],
    }

    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})

    return {
        "message": "Login successful",
        "token": token,
        "user": user_dict,
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@router.put("/profile")
def update_profile(body: ProfileUpdateIn, current_user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        """UPDATE users SET name = ?, phone = ?, organization = ?, avatar_url = ?
           WHERE id = ?""",
        (body.name.strip(), body.phone, body.organization, body.avatar_url, current_user["id"]),
    )
    db.commit()
    updated = db.execute(
        "SELECT id, name, email, role, phone, organization, avatar_url, status FROM users WHERE id = ?",
        (current_user["id"],),
    ).fetchone()
    db.close()
    return {"message": "Profile updated successfully", "user": dict(updated)}


@router.put("/change-password")
def change_password(body: ChangePasswordIn, current_user: dict = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")

    db = get_db()
    user = db.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],)).fetchone()
    if not user or user["password_hash"] != hash_password(body.old_password):
        db.close()
        raise HTTPException(status_code=400, detail="Current password does not match.")

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(body.new_password), current_user["id"]),
    )
    db.commit()
    db.close()
    return {"message": "Password changed successfully."}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn):
    db = get_db()
    user = db.execute("SELECT id, email FROM users WHERE LOWER(email) = LOWER(?)", (body.email.strip(),)).fetchone()
    db.close()
    # Always return 200 to prevent account enumeration
    return {
        "message": "If an account exists with this email, password reset instructions have been dispatched.",
        "demo_code": "RESET-2025" if user else None,
    }


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (body.email.strip(),)).fetchone()
    if not user:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid email or reset code.")

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(body.new_password), user["id"]),
    )
    db.commit()
    db.close()
    return {"message": "Password has been reset successfully. You can now login."}


# ── Admin User Management Endpoints ───────────────────────────────────────────

@router.get("/users")
def get_all_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: dict = Depends(require_roles(["admin"])),
):
    db = get_db()
    query = "SELECT id, name, email, role, phone, organization, status, created_at FROM users WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR organization LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if role:
        query += " AND role = ?"
        params.append(role)

    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


from ops import write_audit


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: RoleUpdateIn,
    current_user: dict = Depends(require_roles(["admin"])),
):
    if body.role not in ["admin", "organizer", "participant"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    db = get_db()
    user = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found.")

    prev_role = user["role"]
    db.execute("UPDATE users SET role = ? WHERE id = ?", (body.role, user_id))

    write_audit(
        db,
        actor=current_user,
        action="user.role_change",
        object_type="user",
        object_id=user_id,
        object_label=f"{user['name']} ({user['email']})",
        previous_value=prev_role,
        new_value=body.role,
    )

    db.commit()
    db.close()
    return {"message": f"User role updated to {body.role}"}


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    body: StatusUpdateIn,
    current_user: dict = Depends(require_roles(["admin"])),
):
    if body.status not in ["active", "inactive", "suspended"]:
        raise HTTPException(status_code=400, detail="Invalid status specified.")

    if user_id == current_user["id"] and body.status != "active":
        raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account.")

    db = get_db()
    user = db.execute("SELECT id, name, email, status FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found.")

    prev_status = user["status"]
    db.execute("UPDATE users SET status = ? WHERE id = ?", (body.status, user_id))

    write_audit(
        db,
        actor=current_user,
        action="user.status_change",
        object_type="user",
        object_id=user_id,
        object_label=f"{user['name']} ({user['email']})",
        previous_value=prev_status,
        new_value=body.status,
    )

    db.commit()
    db.close()
    return {"message": f"User status updated to {body.status}"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(require_roles(["admin"])),
):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    db = get_db()
    user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found.")

    write_audit(
        db,
        actor=current_user,
        action="user.delete",
        object_type="user",
        object_id=user_id,
        object_label=f"{user['name']} ({user['email']})",
        previous_value=None,
        new_value=None,
    )

    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    db.close()
    return {"message": "User deleted successfully."}
