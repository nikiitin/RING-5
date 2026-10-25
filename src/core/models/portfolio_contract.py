"""The current portfolio schema accepted at serialized input boundaries."""

from __future__ import annotations

from typing import Any

CURRENT_PORTFOLIO_SCHEMA_VERSION = 4


class PortfolioVersionError(ValueError):
    """A serialized portfolio does not declare the supported schema version."""


def validate_portfolio_schema(value: dict[str, Any]) -> dict[str, Any]:
    """Validate a current portfolio without rewriting or inferring its content.

    Args:
        value: Decoded portfolio JSON object.

    Returns:
        The validated object, unchanged.

    Raises:
        PortfolioVersionError: The schema marker is absent or unsupported.
        ValueError: Required current portfolio metadata is absent or invalid.
    """
    # [impl->req~ring5.portfolio.schema~1]
    version = value.get("schema_version")
    if type(version) is not int or version != CURRENT_PORTFOLIO_SCHEMA_VERSION:
        raise PortfolioVersionError(
            f"Unsupported portfolio schema_version {version!r}; "
            f"expected {CURRENT_PORTFOLIO_SCHEMA_VERSION}."
        )
    if value.get("version") != "4.0":
        raise ValueError("Portfolio version must be '4.0'.")
    for field in ("parser_strategy", "simulator"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"Portfolio {field} must be non-empty text.")
    if not isinstance(value.get("integrity_manifest"), dict):
        raise ValueError("Portfolio integrity_manifest must be an object.")
    if not isinstance(value.get("environment_metadata"), dict):
        raise ValueError("Portfolio environment_metadata must be an object.")
    return value
