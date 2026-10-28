"""Structural admission for explicit serialized visualization models."""

from dataclasses import fields
from typing import Any


def config_object(value: object, name: str) -> dict[str, Any]:
    """Return an owned object with text keys or reject its supplied shape.

    Args:
        value: Supplied serialized object.
        name: Model or field used in diagnostics.

    Returns:
        Shallow copy with the original field values.

    Raises:
        TypeError: The supplied value is not an object with text keys.
    """
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} must be an object with text field names.")
    return dict(value)


def model_fields(value: object, model: type[Any], name: str) -> dict[str, Any]:
    """Admit supplied model fields while preserving omitted-field defaults.

    Args:
        value: Supplied serialized object.
        model: Dataclass whose current field names are accepted.
        name: Model or field used in diagnostics.

    Returns:
        Shallow copy containing only supported supplied fields.

    Raises:
        TypeError: An object shape or field name is unsupported.
    """
    data = config_object(value, name)
    unsupported = data.keys() - {item.name for item in fields(model)}
    if unsupported:
        raise TypeError(f"Unsupported {name} fields: {sorted(unsupported)}.")
    return data


def config_list(value: object, name: str) -> list[Any]:
    """Return an owned list without interpreting its element values.

    Args:
        value: Supplied serialized array.
        name: Field used in diagnostics.

    Returns:
        Shallow copy containing the original elements.

    Raises:
        TypeError: The supplied value is not a list.
    """
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an array.")
    return list(value)
