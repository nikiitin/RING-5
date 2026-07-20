"""Attach semantic labels and perform explicit, compatible unit conversions."""

from __future__ import annotations

from dataclasses import dataclass
import copy
from typing import Any, Final

import numpy as np
import pandas as pd

from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics

SEMANTICS_ATTR: Final = "ring5.semantic_columns"


@dataclass(frozen=True, slots=True)
class _Unit:
    dimension: str
    scale: float
    offset: float = 0.0


# Values convert to their dimension's base unit as ``value * scale + offset``.
_UNITS: Final[dict[str, _Unit]] = {
    "ns": _Unit("time", 1e-9),
    "us": _Unit("time", 1e-6),
    "µs": _Unit("time", 1e-6),
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
    "µm": _Unit("length", 1e-6),
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

_ALIASES: Final[dict[str, str]] = {
    "μs": "µs",
    "microsecond": "µs",
    "microseconds": "µs",
    "millisecond": "ms",
    "milliseconds": "ms",
    "second": "s",
    "seconds": "s",
    "hour": "h",
    "hours": "h",
    "celsius": "°C",
    "fahrenheit": "°F",
    "kelvin": "K",
    "percent": "%",
    "percentage": "%",
}


class SemanticMetadataService:
    """Keep semantics portable without mutating caller-owned dataframes."""

    @classmethod
    def attach(
        cls,
        data: pd.DataFrame,
        semantics: DatasetSemantics,
    ) -> pd.DataFrame:
        """Return a copy carrying validated metadata in dataframe attributes."""
        # [impl->req~ring5.data.semantic-units~1]
        cls._validate_data(data)
        if not isinstance(semantics, DatasetSemantics):
            raise TypeError("semantics must be a DatasetSemantics value.")
        missing = [column.name for column in semantics.columns if column.name not in data.columns]
        if missing:
            raise KeyError(f"Semantic column {missing[0]!r} does not exist.")
        normalized = DatasetSemantics(
            tuple(
                ColumnSemantics(
                    column.name,
                    column.label,
                    cls.normalize_unit(column.unit) if column.unit else "",
                )
                for column in semantics.columns
            )
        )
        result = data.copy(deep=True)
        result.attrs = dict(data.attrs)
        result.attrs[SEMANTICS_ATTR] = cls.to_payload(normalized)
        return result

    @classmethod
    def inspect(cls, data: pd.DataFrame) -> DatasetSemantics:
        """Decode retained metadata, rejecting malformed external attributes."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Semantic metadata requires a pandas DataFrame.")
        raw = data.attrs.get(SEMANTICS_ATTR, {})
        if raw in (None, {}):
            return DatasetSemantics()
        cls._validate_data(data)
        return cls.from_payload(
            raw, available_columns=tuple(str(column) for column in data.columns)
        )

    @classmethod
    def convert(cls, data: pd.DataFrame, column: str, target_unit: str) -> pd.DataFrame:
        """Return a converted copy and update that column's retained unit."""
        # [impl->req~ring5.data.semantic-units~1]
        cls._validate_data(data)
        if not isinstance(column, str) or column not in data.columns:
            raise KeyError(f"Semantic column {column!r} does not exist.")
        semantics = cls.inspect(data)
        declared = semantics.for_column(column)
        if declared is None or not declared.unit:
            raise ValueError(f"Column {column!r} has no declared source unit.")
        source_name = cls.normalize_unit(declared.unit)
        target_name = cls.normalize_unit(target_unit)
        source, target = _UNITS[source_name], _UNITS[target_name]
        if source.dimension != target.dimension:
            raise ValueError(
                f"Cannot convert {source_name!r} to {target_name!r}: units are not compatible."
            )
        numeric = pd.to_numeric(data[column], errors="coerce")
        invalid = data[column].notna() & numeric.isna()
        if invalid.any():
            raise ValueError(f"Column {column!r} contains non-numeric values.")
        converted = (
            (numeric.astype(float) * source.scale) + source.offset - target.offset
        ) / target.scale
        if not np.isfinite(converted.dropna().to_numpy(dtype=float)).all():
            raise ValueError(f"Converting column {column!r} produced non-finite values.")
        result = data.copy(deep=True)
        result[column] = converted
        updated = DatasetSemantics(
            tuple(
                ColumnSemantics(item.name, item.label, target_name) if item.name == column else item
                for item in semantics.columns
            )
        )
        result.attrs = dict(data.attrs)
        result.attrs[SEMANTICS_ATTR] = cls.to_payload(updated)
        return result

    @staticmethod
    def supported_units() -> tuple[str, ...]:
        """Return canonical units in stable declaration order."""
        return tuple(_UNITS)

    @classmethod
    def enrich_figure_config(
        cls,
        data: pd.DataFrame,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Fill absent axis/dimension labels from retained semantics."""
        # [impl->req~ring5.data.semantic-units~1]
        semantics = cls.inspect(data)
        if not semantics.columns:
            return config
        enriched = copy.deepcopy(config)

        def label_for(column: object) -> str:
            metadata = semantics.for_column(str(column)) if column else None
            return metadata.display_label if metadata is not None else ""

        if not (enriched.get("xlabel") or enriched.get("xaxis_title")):
            x_label = label_for(enriched.get("x"))
            if x_label:
                enriched["xlabel"] = x_label
        if not (enriched.get("ylabel") or enriched.get("yaxis_title")):
            y_columns: list[object] = []
            if enriched.get("y"):
                y_columns = [enriched["y"]]
            elif enriched.get("y_bar"):
                y_columns = [enriched["y_bar"]]
            elif isinstance(enriched.get("y_columns"), list):
                y_columns = enriched["y_columns"]
            y_label = cls._shared_axis_label(semantics, y_columns)
            if y_label:
                enriched["ylabel"] = y_label
        if not enriched.get("ylabel_right"):
            right_label = label_for(enriched.get("y_dot"))
            if right_label:
                enriched["ylabel_right"] = right_label

        dimensions = enriched.get("parallel_dimensions")
        if isinstance(dimensions, list):
            aliases = dict(enriched.get("parallel_labels") or {})
            for column in dimensions:
                inferred = label_for(column)
                if inferred:
                    aliases.setdefault(str(column), inferred)
            if aliases:
                enriched["parallel_labels"] = aliases
        return enriched

    @staticmethod
    def _shared_axis_label(
        semantics: DatasetSemantics,
        columns: list[object],
    ) -> str:
        declared = [semantics.for_column(str(column)) for column in columns]
        metadata = [value for value in declared if value is not None]
        if len(metadata) != len(columns) or not metadata:
            return ""
        if len(metadata) == 1:
            return metadata[0].display_label
        units = {value.unit for value in metadata}
        return f"Value ({metadata[0].unit})" if len(units) == 1 and metadata[0].unit else ""

    @staticmethod
    def normalize_unit(unit: str) -> str:
        """Resolve a canonical unit or a documented human-friendly alias."""
        if not isinstance(unit, str) or not unit.strip():
            raise ValueError("Units must be non-empty strings.")
        resolved = unit.strip()
        canonical = resolved if resolved in _UNITS else _ALIASES.get(resolved.lower())
        if canonical is None:
            choices = ", ".join(_UNITS)
            raise ValueError(f"Unsupported unit {unit!r}. Supported units: {choices}.")
        return canonical

    @staticmethod
    def to_payload(semantics: DatasetSemantics) -> dict[str, dict[str, str]]:
        """Encode semantics as stable JSON-compatible data."""
        return {
            column.name: {"label": column.label, "unit": column.unit}
            for column in semantics.columns
        }

    @classmethod
    def from_payload(
        cls,
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
            columns.append(ColumnSemantics(name, label, cls.normalize_unit(unit) if unit else ""))
        return DatasetSemantics(tuple(columns))

    @staticmethod
    def _validate_data(data: pd.DataFrame) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Semantic metadata requires a pandas DataFrame.")
        if any(not isinstance(column, str) or not column for column in data.columns):
            raise ValueError("Semantic metadata requires non-empty string column names.")
        if data.columns.duplicated().any():
            raise ValueError("Semantic metadata requires unique column names.")
