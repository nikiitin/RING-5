"""Safe, defensive transfer of figure settings and shaping pipelines."""

from __future__ import annotations

import copy
from collections.abc import Sequence

from src.core.models.plot_protocol import PlotProtocol
from src.core.models.visualization.plot_transfer_result import (
    PlotTransferMode,
    PlotTransferResult,
)

SETTING_SECTIONS: dict[str, frozenset[str]] = {
    "labels": frozenset({"title", "xlabel", "ylabel", "ylabel_right", "legend_title"}),
    "layout": frozenset(
        {
            "width",
            "height",
            "width_inches",
            "height_inches",
            "document_width_preset",
            "margin_t",
            "margin_b",
            "margin_l",
            "margin_r",
            "margin_pad",
            "automargin",
            "paper_bgcolor",
            "plot_bgcolor",
        }
    ),
    "typography": frozenset(
        {
            "font_family",
            "title_font_size",
            "xaxis_title_font_size",
            "yaxis_title_font_size",
            "xaxis_tickfont_size",
            "yaxis_tickfont_size",
            "legend_font_size",
            "legend_title_font_size",
        }
    ),
    "axes": frozenset(
        {
            "range_x",
            "range_y",
            "range_y2",
            "xaxis_dtick",
            "yaxis_dtick",
            "xaxis_tickangle",
            "show_x_grid",
            "show_y_grid",
            "show_x_tick_marks",
            "show_y_tick_marks",
            "axis_color",
            "xaxis_order",
            "group_order",
        }
    ),
    "legends": frozenset(
        {
            "legend_labels",
            "legend_order",
            "legend_orientation",
            "legend_x",
            "legend_y",
            "legend_xanchor",
            "legend_yanchor",
            "legend_bgcolor",
            "legend_border_color",
            "legend_border_width",
            "legend_ncols",
        }
    ),
    "colors": frozenset({"color_palette", "series_styles", "enable_stripes", "bar_border_color"}),
    "annotations": frozenset(
        {
            "shapes",
            "reference_line_enabled",
            "reference_line_y",
            "reference_line_color",
            "reference_line_width",
            "reference_line_style",
            "show_values",
            "text_format",
            "text_position",
            "text_color_mode",
            "text_color",
            "text_rotation",
            "text_font_size",
        }
    ),
}


def _columns(plot: PlotProtocol, *, source: bool) -> set[str]:
    data = plot.source_data if source else plot.processed_data
    return set(data.columns) if data is not None else set()


def _require_schema(source: PlotProtocol, target: PlotProtocol, *, source_data: bool) -> None:
    source_columns = _columns(source, source=source_data)
    target_columns = _columns(target, source=source_data)
    missing = sorted(source_columns - target_columns)
    if missing:
        data_kind = "source" if source_data else "processed"
        raise ValueError(
            f"Destination plot is missing {data_kind} columns required by the source: "
            + ", ".join(missing)
            + "."
        )


def configuration_replacement_reason(
    source: PlotProtocol,
    target: PlotProtocol,
) -> str | None:
    """Return why a complete configuration replacement is unsafe, if anything."""
    if source.plot_type != target.plot_type:
        return "Complete configurations can only be copied between the same plot type."
    source_columns = _columns(source, source=False)
    target_columns = _columns(target, source=False)
    missing = sorted(source_columns - target_columns)
    if missing:
        return (
            "Destination plot is missing processed columns required by the source: "
            + ", ".join(missing)
            + "."
        )
    return None


def copy_plot_content(
    source: PlotProtocol,
    target: PlotProtocol,
    mode: PlotTransferMode,
    *,
    sections: Sequence[str] = (),
) -> PlotTransferResult:
    # [impl->req~ring5.plots.copy-settings-pipeline~1]
    """Copy one validated slice of a plot into another plot atomically."""
    if source.plot_id == target.plot_id:
        raise ValueError("Choose two different plots for a copy operation.")
    if mode not in ("settings", "configuration", "pipeline"):
        raise ValueError("Copy mode must be 'settings', 'configuration', or 'pipeline'.")

    if mode == "settings":
        requested = tuple(sections)
        if not requested:
            raise ValueError("Choose at least one figure-settings section to copy.")
        unknown = sorted(set(requested) - SETTING_SECTIONS.keys())
        if unknown:
            raise ValueError("Unknown figure-settings sections: " + ", ".join(unknown) + ".")
        keys = sorted(set().union(*(SETTING_SECTIONS[name] for name in requested)))
        copied = tuple(key for key in keys if key in source.config)
        if not copied:
            raise ValueError("The source plot has no values in the selected settings sections.")
        updated = copy.deepcopy(target.config)
        for key in copied:
            updated[key] = copy.deepcopy(source.config[key])
        target.config = updated
        target.invalidate_figure()
        return PlotTransferResult(source.plot_id, target.plot_id, mode, copied_keys=copied)

    if mode == "configuration":
        replacement_reason = configuration_replacement_reason(source, target)
        if replacement_reason is not None:
            raise ValueError(replacement_reason)
        target.config = copy.deepcopy(source.config)
        target.legend_mappings = copy.deepcopy(source.legend_mappings)
        target.legend_mappings_by_column = copy.deepcopy(source.legend_mappings_by_column)
        target.invalidate_figure()
        return PlotTransferResult(
            source.plot_id,
            target.plot_id,
            mode,
            copied_keys=tuple(sorted(source.config)),
        )

    _require_schema(source, target, source_data=True)
    target.pipeline = copy.deepcopy(source.pipeline)
    target.pipeline_counter = source.pipeline_counter
    target.replace_processed_data(None)
    return PlotTransferResult(
        source.plot_id,
        target.plot_id,
        mode,
        pipeline_steps=len(target.pipeline),
        requires_finalize=True,
    )


__all__ = [
    "SETTING_SECTIONS",
    "configuration_replacement_reason",
    "copy_plot_content",
]
