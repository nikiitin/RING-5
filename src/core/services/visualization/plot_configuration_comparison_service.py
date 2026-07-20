"""Field-level, non-mutating comparison of live plot configurations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.core.models.plot_protocol import PlotProtocol
from src.core.models.visualization.plot_configuration_comparison import (
    ConfigurationChange,
    ConfigurationDifference,
    PlotConfigurationComparison,
)
from src.core.services.visualization.plot_transfer_service import (
    SETTING_SECTIONS,
    configuration_replacement_reason,
)

_MISSING_DISPLAY = "—"
_DATA_MAPPING_KEYS = frozenset(
    {
        "x",
        "y",
        "y2",
        "color",
        "group",
        "facet",
        "size",
        "text",
        "hover_data",
        "columns",
        "y_columns",
    }
)
_SECTION_LABELS = {
    "labels": "Titles and labels",
    "layout": "Layout and dimensions",
    "typography": "Typography",
    "axes": "Axes and ordering",
    "legends": "Legends",
    "colors": "Colors and series styles",
    "annotations": "Annotations and data labels",
}


def _section_for(root: str) -> str:
    if root in ("legend_mappings", "legend_mappings_by_column"):
        return _SECTION_LABELS["legends"]
    if root in _DATA_MAPPING_KEYS:
        return "Data mappings"
    for section, keys in SETTING_SECTIONS.items():
        if root in keys:
            return _SECTION_LABELS[section]
    return "Plot-specific settings"


def _flatten(
    value: Any,
    *,
    path: str,
    root: str,
    output: dict[str, tuple[str, Any]],
) -> None:
    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=lambda item: str(item)):
            child = str(key)
            _flatten(
                value[key],
                path=f"{path}.{child}" if path else child,
                root=root or child,
                output=output,
            )
        return
    output[path] = (root, value)


def _plot_values(plot: PlotProtocol) -> dict[str, tuple[str, Any]]:
    values: dict[str, tuple[str, Any]] = {}
    for key in sorted(plot.config):
        _flatten(plot.config[key], path=key, root=key, output=values)
    _flatten(
        plot.legend_mappings,
        path="legend_mappings",
        root="legend_mappings",
        output=values,
    )
    _flatten(
        plot.legend_mappings_by_column,
        path="legend_mappings_by_column",
        root="legend_mappings_by_column",
        output=values,
    )
    return values


def _json_fallback(value: Any) -> str:
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return str(item())
        except (TypeError, ValueError):
            pass
    return repr(value)


def _display(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=_json_fallback,
        )
    except (TypeError, ValueError, OverflowError):
        return repr(value)


def compare_plot_configurations(
    source: PlotProtocol,
    destination: PlotProtocol,
) -> PlotConfigurationComparison:
    # [impl->req~ring5.plots.configuration-comparison~1]
    """Compare configuration leaves without changing either live plot."""
    if source.plot_id == destination.plot_id:
        raise ValueError("Choose two different plots for configuration comparison.")

    source_values = _plot_values(source)
    destination_values = _plot_values(destination)
    all_paths = set(source_values) | set(destination_values)
    paths = sorted(
        path for path in all_paths if not any(other.startswith(f"{path}.") for other in all_paths)
    )
    differences: list[ConfigurationDifference] = []
    matching_fields = 0

    for path in paths:
        source_entry = source_values.get(path)
        destination_entry = destination_values.get(path)
        source_display = _display(source_entry[1]) if source_entry else _MISSING_DISPLAY
        destination_display = (
            _display(destination_entry[1]) if destination_entry else _MISSING_DISPLAY
        )
        if source_entry and destination_entry and source_display == destination_display:
            matching_fields += 1
            continue
        if source_entry is None:
            change: ConfigurationChange = "destination_only"
            root = destination_entry[0] if destination_entry else path.split(".", 1)[0]
        elif destination_entry is None:
            change = "source_only"
            root = source_entry[0]
        else:
            change = "changed"
            root = source_entry[0]
        differences.append(
            ConfigurationDifference(
                path=path,
                section=_section_for(root),
                change=change,
                source_value=source_display,
                destination_value=destination_display,
            )
        )

    replacement_reason = configuration_replacement_reason(source, destination)
    return PlotConfigurationComparison(
        source_plot_id=source.plot_id,
        destination_plot_id=destination.plot_id,
        source_name=source.name,
        destination_name=destination.name,
        source_plot_type=source.plot_type,
        destination_plot_type=destination.plot_type,
        differences=tuple(differences),
        matching_fields=matching_fields,
        total_fields=len(paths),
        can_replace=replacement_reason is None,
        replacement_reason=replacement_reason,
    )


__all__ = ["compare_plot_configurations"]
