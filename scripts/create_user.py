"""Create or update a local prototype user without exposing the password."""

import argparse
from datetime import UTC, datetime
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.entities import UserEntity
from app.database.session import get_session_factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a Jira AI Intelligence user.")
    parser.add_argument("username")
    parser.add_argument(
        "--role",
        choices=("viewer", "admin"),
        default="viewer",
    )
    parser.add_argument("--first-name")
    parser.add_argument("--last-name")
    parser.add_argument("--email")
    args = parser.parse_args()

    first_name = _clean_optional(args.first_name, "First name", 100)
    last_name = _clean_optional(args.last_name, "Last name", 100)
    email = _clean_email(args.email)

    password = getpass("Password (minimum 8 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")

    with get_session_factory()() as session:
        user = session.scalar(select(UserEntity).where(UserEntity.username == args.username))
        if email is not None:
            email_owner = session.scalar(select(UserEntity).where(UserEntity.email == email))
            if email_owner is not None and email_owner.id != getattr(user, "id", None):
                raise SystemExit("Email is already assigned to another user.")
        if user is None:
            user = UserEntity(
                username=args.username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=hash_password(password),
                role=args.role,
                is_active=True,
                created_at=datetime.now(UTC),
            )
            session.add(user)
            action = "created"
        else:
            user.password_hash = hash_password(password)
            user.role = args.role
            user.is_active = True
            if args.first_name is not None:
                user.first_name = first_name
            if args.last_name is not None:
                user.last_name = last_name
            if args.email is not None:
                user.email = email
            action = "updated"
        session.commit()

    print(f"User '{args.username}' {action} with role '{args.role}'.")


def _clean_optional(value: str | None, label: str, maximum: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise SystemExit(f"{label} cannot be empty when supplied.")
    if len(cleaned) > maximum:
        raise SystemExit(f"{label} cannot exceed {maximum} characters.")
    return cleaned


def _clean_email(value: str | None) -> str | None:
    cleaned = _clean_optional(value, "Email", 254)
    if cleaned is None:
        return None
    local, separator, domain = cleaned.partition("@")
    if not separator or not local or "." not in domain:
        raise SystemExit("Email must be a valid address.")
    return cleaned.lower()


if __name__ == "__main__":
    main()
