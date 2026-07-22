"""Validation and deterministic panel discovery for small multiples."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.core.models.visualization.small_multiples_spec import FacetPanel, SmallMultiplesSpec


def _browser_scalar(value: Any) -> Any:
    """Normalize pandas/numpy scalars while retaining exact filter semantics."""
    if value is None or value is pd.NA:
        return None
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _key(value: Any, size: int, *, field: str) -> tuple[Any, ...]:
    """Normalize a public single- or multi-column facet key."""
    if size == 1 and not isinstance(value, (tuple, list)):
        values = (value,)
    elif isinstance(value, (tuple, list)):
        values = tuple(value)
    else:
        raise ValueError(f"{field} entries need {size} values, one per facet column.")
    if len(values) != size:
        raise ValueError(f"{field} entries need {size} values, one per facet column.")
    normalized = tuple(_browser_scalar(item) for item in values)
    try:
        hash(normalized)
    except TypeError as exc:
        raise ValueError(f"{field} values must be scalar.") from exc
    return normalized


def _display_value(value: Any) -> str:
    if value is None:
        return "Missing"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _default_title(columns: tuple[str, ...], values: tuple[Any, ...]) -> str:
    return " · ".join(
        f"{column}: {_display_value(value)}" for column, value in zip(columns, values)
    )


def create_small_multiples_spec(
    plot_id: int,
    data: pd.DataFrame,
    facet_columns: Sequence[str],
    *,
    columns: int = 3,
    order: Sequence[Any] | None = None,
    labels: Mapping[Any, str] | None = None,
    title: str = "",
    width: int = 1200,
    panel_height: int = 320,
    shared_xaxes: bool = True,
    shared_yaxes: bool = True,
    shared_legend: bool = True,
    x_title: str = "",
    y_title: str = "",
) -> SmallMultiplesSpec:
    # [impl->req~ring5.plots.small-multiples~1]
    """Discover facet combinations and create a deterministic grid specification."""
    if isinstance(plot_id, bool) or not isinstance(plot_id, int):
        raise ValueError("Small-multiples plot_id must be an integer.")
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Small-multiples data must be a pandas DataFrame.")
    if data.empty:
        raise ValueError("Small multiples cannot be created from empty data.")
    requested: tuple[str, ...]
    if isinstance(facet_columns, (str, bytes)):
        requested = (str(facet_columns),)
    else:
        requested = tuple(facet_columns)
    if not requested:
        raise ValueError("Choose at least one categorical facet column.")
    if any(not isinstance(column, str) or not column.strip() for column in requested):
        raise ValueError("Facet column names must be non-empty strings.")
    if len(set(requested)) != len(requested):
        raise ValueError("Facet columns must be unique.")
    missing = [column for column in requested if column not in data.columns]
    if missing:
        raise ValueError("Unknown facet columns: " + ", ".join(missing) + ".")
    numeric = [
        column
        for column in requested
        if is_numeric_dtype(data[column].dtype) and not is_bool_dtype(data[column].dtype)
    ]
    if numeric:
        raise ValueError("Facet columns must be categorical, not numeric: " + ", ".join(numeric))
    if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
        raise ValueError("Small-multiples columns must be a positive integer.")
    if isinstance(panel_height, bool) or not isinstance(panel_height, int) or panel_height < 120:
        raise ValueError("Small-multiples panel_height must be an integer of at least 120 pixels.")

    discovered = [
        tuple(_browser_scalar(value) for value in row)
        for row in data.loc[:, list(requested)].drop_duplicates().itertuples(index=False, name=None)
    ]
    if len(discovered) < 2:
        raise ValueError(
            "Small multiples needs at least two facet groups; the selected columns produce "
            f"{len(discovered)}."
        )

    ordered: list[tuple[Any, ...]] = []
    if order is not None:
        for entry in order:
            normalized = _key(entry, len(requested), field="Facet order")
            if normalized not in discovered:
                raise ValueError(f"Facet order contains an unknown group: {normalized!r}.")
            if normalized in ordered:
                raise ValueError(f"Facet order contains a duplicate group: {normalized!r}.")
            ordered.append(normalized)
    ordered.extend(value for value in discovered if value not in ordered)

    label_map: dict[tuple[Any, ...], str] = {}
    for raw_key, raw_label in (labels or {}).items():
        normalized = _key(raw_key, len(requested), field="Facet label")
        if normalized not in discovered:
            raise ValueError(f"Facet labels contain an unknown group: {normalized!r}.")
        if not isinstance(raw_label, str) or not raw_label.strip():
            raise ValueError("Facet labels must be non-empty strings.")
        label_map[normalized] = raw_label.strip()

    panels = tuple(
        FacetPanel(values=values, title=label_map.get(values, _default_title(requested, values)))
        for values in ordered
    )
    rows = (len(panels) + columns - 1) // columns
    return SmallMultiplesSpec(
        plot_id=plot_id,
        facet_columns=requested,
        panels=panels,
        rows=rows,
        columns=columns,
        title=title.strip(),
        width=width,
        height=max(240, rows * panel_height),
        shared_xaxes=shared_xaxes,
        shared_yaxes=shared_yaxes,
        shared_legend=shared_legend,
        x_title=x_title.strip(),
        y_title=y_title.strip(),
    )


__all__ = ["create_small_multiples_spec"]
