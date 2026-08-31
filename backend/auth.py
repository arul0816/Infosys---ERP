import hmac
import hashlib
import base64
import json
import time
from typing import Optional, List
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_db

SECRET_KEY = "eventsphere_production_secret_key_2025_infy"
TICKET_SECRET = "eventsphere_ticket_qr_hmac_secret_2025"

security_bearer = HTTPBearer(auto_error=False)


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(data: dict, expires_in_seconds: int = 86400 * 7) -> str:
    """Generate a signed HMAC-SHA256 JWT-compatible token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds
    payload["iat"] = int(time.time())

    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_sig = base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify HMAC-SHA256 token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        encoded_header, encoded_payload, encoded_sig = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = base64url_encode(
            hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        )

        if not hmac.compare_digest(encoded_sig, expected_sig):
            return None

        payload_bytes = base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp") and payload["exp"] < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def sign_ticket_payload(ticket_id: str, attendee_id: int, event_id: int, email: str) -> str:
    """Generate a tamper-proof cryptographic QR payload."""
    payload = {
        "tid": ticket_id,
        "aid": attendee_id,
        "eid": event_id,
        "em": email[:3] + "***",
        "ts": int(time.time()),
    }
    raw = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(TICKET_SECRET.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"ESP:{ticket_id}:{event_id}:{attendee_id}:{sig}"


def verify_ticket_payload(token_str: str) -> tuple[bool, Optional[dict]]:
    """Validate cryptographic QR ticket payload and return data."""
    try:
        # Expected format ESP:<ticket_id>:<event_id>:<attendee_id>:<sig>
        parts = token_str.strip().split(":")
        if len(parts) != 5 or parts[0] != "ESP":
            # Fallback format or plain ticket ID
            return False, None

        _, ticket_id, event_id_str, attendee_id_str, sig = parts
        event_id = int(event_id_str)
        attendee_id = int(attendee_id_str)

        db = get_db()
        ticket = db.execute(
            """SELECT t.*, a.email, a.name, a.status as attendee_status, e.name as event_name
               FROM tickets t
               JOIN attendees a ON t.attendee_id = a.id
               JOIN events e ON t.event_id = e.id
               WHERE t.ticket_id = ? AND t.event_id = ? AND t.attendee_id = ?""",
            (ticket_id, event_id, attendee_id),
        ).fetchone()
        db.close()

        if not ticket:
            return False, None

        # Verify signature matches the cryptographic token registered for the ticket
        if ticket["qr_token"] and ticket["qr_token"].strip() != token_str.strip():
            return False, None

        return True, dict(ticket)
    except Exception:
        return False, None



def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
    """FastAPI dependency to retrieve authenticated user from Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    db = get_db()
    user = db.execute("SELECT id, name, email, role, avatar_url, phone, organization, status FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    if user["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated or suspended.",
        )

    return dict(user)


def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[dict]:
    """FastAPI dependency for optional authenticated user."""
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    db = get_db()
    user = db.execute("SELECT id, name, email, role, avatar_url, phone, organization, status FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return dict(user) if user and user["status"] == "active" else None


def require_roles(allowed_roles: List[str], auto_error: bool = True):
    """Role-based authorization dependency factory."""
    if auto_error:
        # Strict mode: requires authentication and specific role
        def role_checker(current_user: dict = Depends(get_current_user)):
            if current_user["role"] not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: requires one of the following roles: {', '.join(allowed_roles)}",
                )
            return current_user
        return role_checker
    else:
        # Optional mode: authentication optional, role check if authenticated
        def optional_role_checker(current_user: Optional[dict] = Depends(get_optional_current_user)):
            if current_user and current_user["role"] not in allowed_roles:
                return None  # User authenticated but doesn't have required role
            return current_user
        return optional_role_checker
