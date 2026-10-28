"""Exact JSON scalar identities for typed operand controls."""

import json


def scalar_token(value: object) -> str:
    """Identify a finite JSON scalar without merging integer and text labels."""
    if value is not None and type(value) not in (str, int, float, bool):
        raise ValueError("This operand is not a JSON scalar the editor can represent.")
    try:
        return json.dumps([type(value).__name__, value], allow_nan=False)
    except ValueError as exc:
        raise ValueError("Non-finite scalar operands cannot be edited.") from exc
