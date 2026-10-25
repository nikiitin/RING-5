"""Pure semantic metadata values, payload validation and physical unit definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics

SEMANTICS_ATTR: Final = "ring5.semantic_columns"


@dataclass(frozen=True, slots=True)
class _Unit:
    dimension: str
    scale: float
    offset: float = 0.0


# Values convert to their dimension's base unit as ``value * scale + offset``.
UNIT_DEFINITIONS: Final[dict[str, _Unit]] = {
    "ns": _Unit("time", 1e-9),
    "us": _Unit("time", 1e-6),
    "ms": _Unit("time", 1e-3),
    "s": _Unit("time", 1.0),
    "min": _Unit("time", 60.0),
    "h": _Unit("time", 3600.0),
    "Hz": _Unit("frequency", 1.0),
    "kHz": _Unit("frequency", 1e3),
    "MHz": _Unit("frequency", 1e6),
    "GHz": _Unit("frequency", 1e9),
    "nm": _Unit("length", 1e-9),
    "um": _Unit("length", 1e-6),
    "mm": _Unit("length", 1e-3),
    "cm": _Unit("length", 1e-2),
    "m": _Unit("length", 1.0),
    "km": _Unit("length", 1e3),
    "B": _Unit("data", 1.0),
    "KB": _Unit("data", 1e3),
    "MB": _Unit("data", 1e6),
    "GB": _Unit("data", 1e9),
    "TB": _Unit("data", 1e12),
    "KiB": _Unit("data", 1024.0),
    "MiB": _Unit("data", 1024.0**2),
    "GiB": _Unit("data", 1024.0**3),
    "W": _Unit("power", 1.0),
    "mW": _Unit("power", 1e-3),
    "kW": _Unit("power", 1e3),
    "J": _Unit("energy", 1.0),
    "mJ": _Unit("energy", 1e-3),
    "kJ": _Unit("energy", 1e3),
    "V": _Unit("voltage", 1.0),
    "mV": _Unit("voltage", 1e-3),
    "kV": _Unit("voltage", 1e3),
    "A": _Unit("current", 1.0),
    "mA": _Unit("current", 1e-3),
    "K": _Unit("temperature", 1.0),
    "°C": _Unit("temperature", 1.0, 273.15),
    "°F": _Unit("temperature", 5.0 / 9.0, 255.3722222222222),
    "ratio": _Unit("ratio", 1.0),
    "%": _Unit("ratio", 0.01),
}


def validate_unit(unit: str) -> str:
    """Return an exact canonical unit token or raise ``ValueError``."""
    if not isinstance(unit, str) or not unit:
        raise ValueError("Units must be non-empty strings.")
    if unit not in UNIT_DEFINITIONS:
        choices = ", ".join(UNIT_DEFINITIONS)
        raise ValueError(f"Unsupported unit {unit!r}. Supported units: {choices}.")
    return unit


def semantics_to_payload(semantics: DatasetSemantics) -> dict[str, dict[str, str]]:
    """Encode semantics as stable JSON-compatible data."""
    return {
        column.name: {"label": column.label, "unit": column.unit} for column in semantics.columns
    }


def semantics_from_payload(
    payload: Any,
    *,
    available_columns: tuple[str, ...] | None = None,
) -> DatasetSemantics:
    """Decode and validate metadata from snapshots or portfolios."""
    if not isinstance(payload, dict):
        raise ValueError("Semantic metadata must map column names to labels and units.")
    columns: list[ColumnSemantics] = []
    for name, values in payload.items():
        if not isinstance(name, str) or not isinstance(values, dict):
            raise ValueError("Semantic metadata entries are invalid.")
        label, unit = values.get("label", ""), values.get("unit", "")
        if not isinstance(label, str) or not isinstance(unit, str):
            raise ValueError("Semantic labels and units must be strings.")
        if available_columns is not None and name not in available_columns:
            raise ValueError(f"Semantic column {name!r} does not exist in the dataset.")
        columns.append(ColumnSemantics(name, label, validate_unit(unit) if unit else ""))
    return DatasetSemantics(tuple(columns))


def validate_semantic_data(data: pd.DataFrame) -> None:
    """Require the unique, non-empty string names used by semantic metadata."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Semantic metadata requires a pandas DataFrame.")
    if any(not isinstance(column, str) or not column for column in data.columns):
        raise ValueError("Semantic metadata requires non-empty string column names.")
    if data.columns.duplicated().any():
        raise ValueError("Semantic metadata requires unique column names.")


def inspect_semantics(data: pd.DataFrame) -> DatasetSemantics:
    """Decode retained semantic values without mutating the dataframe."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Semantic metadata requires a pandas DataFrame.")
    raw = data.attrs.get(SEMANTICS_ATTR, {})
    if raw in (None, {}):
        return DatasetSemantics()
    validate_semantic_data(data)
    return semantics_from_payload(
        raw, available_columns=tuple(str(column) for column in data.columns)
    )
