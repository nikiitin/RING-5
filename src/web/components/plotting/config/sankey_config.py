"""Human-first configuration controls for Sankey diagrams."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import detect_column_types
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.web.models.plot_models import PlotConfig

_ARRANGEMENTS = {
    "Snap nodes into columns": "snap",
    "Keep links perpendicular": "perpendicular",
    "Allow free node movement": "freeform",
    "Keep computed positions fixed": "fixed",
}
_COLOR_MODES = {
    "Match each link's source": "source",
    "Match each link's target": "target",
    "Use one link color": "uniform",
}
_LABEL_MODES = {
    "Node names": "names",
    "Node names and flow totals": "names_with_totals",
    "Hide node labels": "hidden",
}


def _index(options: Sequence[object], saved: object, fallback: int = 0) -> int:
    return options.index(saved) if saved in options else fallback


def _saved_label(mapping: dict[str, str], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.sankey~1]
    """Render mappings plus plain-language labels, colors, and layout controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    all_columns = list(data.columns)
    mapping_column, label_column = st.columns(2)
    with mapping_column:
        source: str = st.selectbox(
            "Source nodes",
            options=all_columns,
            index=_index(all_columns, saved_config.get("sankey_source")),
            key=f"sankey_source_{plot_id}",
        )
        target: str = st.selectbox(
            "Target nodes",
            options=all_columns,
            index=_index(
                all_columns, saved_config.get("sankey_target"), min(1, len(all_columns) - 1)
            ),
            key=f"sankey_target_{plot_id}",
        )
        value: str = st.selectbox(
            "Flow value",
            options=numeric_cols,
            index=_index(numeric_cols, saved_config.get("sankey_value")),
            key=f"sankey_value_{plot_id}",
        )
        label_options: list[str | None] = [None, *all_columns]
        link_label: str | None = st.selectbox(
            "Link label (optional)",
            options=label_options,
            index=_index(label_options, saved_config.get("sankey_label")),
            key=f"sankey_label_{plot_id}",
        )
    with label_column:
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"Flow from {source} to {target}") or ""),
            default_xlabel="",
            default_ylabel="",
            include_legend_title=False,
        )

    st.markdown("#### Flow labels and arrangement")
    labels_column, arrangement_column = st.columns(2)
    with labels_column:
        label_choice = st.selectbox(
            "Node labels",
            options=list(_LABEL_MODES),
            index=list(_LABEL_MODES).index(
                _saved_label(_LABEL_MODES, saved_config.get("sankey_label_mode"), "Node names")
            ),
            key=f"sankey_label_mode_{plot_id}",
        )
        show_link_labels = st.checkbox(
            "Show labels on links",
            value=bool(saved_config.get("sankey_show_link_labels", bool(link_label))),
            disabled=link_label is None,
            key=f"sankey_show_link_labels_{plot_id}",
        )
        number_format = st.text_input(
            "Flow number format",
            value=str(saved_config.get("sankey_number_format", ".4g")),
            help="Used when node labels include totals.",
            key=f"sankey_number_format_{plot_id}",
        )
    with arrangement_column:
        arrangement_choice = st.selectbox(
            "Node arrangement",
            options=list(_ARRANGEMENTS),
            index=list(_ARRANGEMENTS).index(
                _saved_label(
                    _ARRANGEMENTS,
                    saved_config.get("sankey_arrangement"),
                    "Snap nodes into columns",
                )
            ),
            key=f"sankey_arrangement_{plot_id}",
        )
        node_pad = st.slider(
            "Space between nodes",
            min_value=0,
            max_value=60,
            value=int(saved_config.get("sankey_node_pad", 15)),
            key=f"sankey_node_pad_{plot_id}",
        )
        node_thickness = st.slider(
            "Node thickness",
            min_value=5,
            max_value=60,
            value=int(saved_config.get("sankey_node_thickness", 20)),
            key=f"sankey_node_thickness_{plot_id}",
        )

    st.markdown("#### Flow colors")
    color_column, style_column = st.columns(2)
    with color_column:
        color_choice = st.radio(
            "Link colors",
            options=list(_COLOR_MODES),
            index=list(_COLOR_MODES).index(
                _saved_label(
                    _COLOR_MODES,
                    saved_config.get("sankey_color_mode"),
                    "Match each link's source",
                )
            ),
            key=f"sankey_color_mode_{plot_id}",
        )
        link_color = st.color_picker(
            "Single link color",
            value=str(saved_config.get("sankey_link_color", "#7f7f7f")),
            disabled=_COLOR_MODES[color_choice] != "uniform",
            key=f"sankey_link_color_{plot_id}",
        )
    with style_column:
        link_opacity = st.slider(
            "Link opacity",
            min_value=0.1,
            max_value=1.0,
            value=float(saved_config.get("sankey_link_opacity", 0.35)),
            step=0.05,
            key=f"sankey_link_opacity_{plot_id}",
        )
        node_line_color = st.color_picker(
            "Node border color",
            value=str(saved_config.get("sankey_node_line_color", "#333333")),
            key=f"sankey_node_line_color_{plot_id}",
        )
        node_line_width = st.slider(
            "Node border width",
            min_value=0.0,
            max_value=5.0,
            value=float(saved_config.get("sankey_node_line_width", 0.5)),
            step=0.5,
            key=f"sankey_node_line_width_{plot_id}",
        )

    return {
        "x": source,
        "y": value,
        "sankey_source": source,
        "sankey_target": target,
        "sankey_value": value,
        "sankey_label": link_label,
        "sankey_label_mode": _LABEL_MODES[label_choice],
        "sankey_show_link_labels": show_link_labels,
        "sankey_number_format": number_format,
        "sankey_arrangement": _ARRANGEMENTS[arrangement_choice],
        "sankey_node_pad": node_pad,
        "sankey_node_thickness": node_thickness,
        "sankey_color_mode": _COLOR_MODES[color_choice],
        "sankey_link_color": link_color,
        "sankey_link_opacity": link_opacity,
        "sankey_node_line_color": node_line_color,
        "sankey_node_line_width": node_line_width,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
