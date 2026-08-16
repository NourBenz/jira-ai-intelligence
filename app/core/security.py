"""Password hashing and signed access-token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import Settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-used-only-to-equalize-login-work")


def hash_password(password: str) -> str:
    """Hash a password with the recommended Argon2 configuration."""
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing hashing-library exceptions."""
    try:
        return password_hash.verify(password, encoded_hash)
    except (TypeError, ValueError, UnknownHashError):
        return False


def create_access_token(
    user_id: int,
    role: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Create a short-lived signed token and return it with its TTL."""
    issued_at = now or datetime.now(UTC)
    lifetime = timedelta(minutes=settings.jwt_access_token_minutes)
    expires_at = issued_at + lifetime
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=ALGORITHM,
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Validate a token's signature, expiry, and required claims."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "role", "exp", "iat"]},
        )
    except InvalidTokenError as error:
        raise ValueError("Invalid or expired access token.") from error

    if payload.get("role") not in {"viewer", "admin"}:
        raise ValueError("Invalid access-token role.")
    try:
        int(payload["sub"])
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid access-token subject.") from error
    return payload
