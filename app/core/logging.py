"""Application logging configuration."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure concise application logs without sensitive request data."""
    logging.basicConfig(
        level=level,
        format=("%(asctime)s %(levelname)s %(name)s %(message)s"),
    )
