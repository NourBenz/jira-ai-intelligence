"""Prepare container-only configuration before executing a backend command."""

import os
import sys
from collections.abc import MutableMapping, Sequence

from sqlalchemy.engine import URL


def configure_database_url(environment: MutableMapping[str, str]) -> None:
    """Build a safely encoded PostgreSQL URL from container environment fields."""
    host = environment.get("DATABASE_HOST")
    if not host:
        return

    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not environment.get(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing container database settings: {names}")

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=environment["POSTGRES_USER"],
        password=environment["POSTGRES_PASSWORD"],
        host=host,
        port=int(environment.get("DATABASE_PORT", "5432")),
        database=environment["POSTGRES_DB"],
    )
    environment["DATABASE_URL"] = database_url.render_as_string(hide_password=False)


def main(arguments: Sequence[str] | None = None) -> None:
    """Configure the environment and replace this process with the command."""
    command = list(sys.argv[1:] if arguments is None else arguments)
    if not command:
        raise RuntimeError("A container command is required.")
    configure_database_url(os.environ)
    # Docker supplies this argv directly; no shell parsing or string interpolation occurs.
    os.execvp(command[0], command)  # nosec B606


if __name__ == "__main__":
    main()
