"""Human-first configuration controls for waterfall charts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_xy_selectors,
)
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.web.models.plot_models import PlotConfig


def _saved_categories(saved: object, options: list[str]) -> list[str]:
    if not isinstance(saved, list):
        return []
    return [str(value) for value in saved if str(value) in options]


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.waterfall~1]
    """Render mappings and explain every waterfall-specific control in plain language."""
    numeric_cols, categorical_cols = detect_column_types(data)
    mapping_column, label_column = st.columns(2)
    with mapping_column:
        x_column, y_column = render_xy_selectors(
            saved_config,
            plot_id,
            numeric_cols,
            categorical_cols,
            x_label="X-axis steps (in order)",
            y_label="Y-axis change or level",
        )
    with label_column:
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"How {y_column} changes") or ""),
            default_xlabel=str(saved_config.get("xlabel", x_column) or ""),
            default_ylabel=str(saved_config.get("ylabel", y_column) or ""),
            include_legend_title=False,
        )

    category_options = [str(value) for value in data[x_column].drop_duplicates()]
    st.markdown("#### Waterfall steps")
    st.caption(
        "Ordinary steps add to the running total. Absolute steps reset it; subtotals show the "
        "current level without changing it."
    )
    meaning_column, total_column = st.columns(2)
    with meaning_column:
        absolute = st.multiselect(
            "Steps that set an absolute level",
            options=category_options,
            default=_saved_categories(saved_config.get("waterfall_absolute"), category_options),
            key=f"waterfall_absolute_{plot_id}",
        )
        subtotal_options = [value for value in category_options if value not in absolute]
        subtotals = st.multiselect(
            "Steps that display a subtotal",
            options=subtotal_options,
            default=_saved_categories(saved_config.get("waterfall_subtotals"), subtotal_options),
            key=f"waterfall_subtotals_{plot_id}",
        )
    with total_column:
        final_total = st.checkbox(
            "Add a final total",
            value=bool(saved_config.get("waterfall_final_total", True)),
            key=f"waterfall_final_total_{plot_id}",
        )
        total_label = st.text_input(
            "Final total label",
            value=str(saved_config.get("waterfall_total_label", "Total")),
            disabled=not final_total,
            key=f"waterfall_total_label_{plot_id}",
        )

    st.markdown("#### Connectors and values")
    connector_column, value_column = st.columns(2)
    with connector_column:
        connectors = st.checkbox(
            "Connect each running level",
            value=bool(saved_config.get("waterfall_connectors", True)),
            key=f"waterfall_connectors_{plot_id}",
        )
        connector_width = st.slider(
            "Connector width",
            min_value=0.5,
            max_value=5.0,
            value=float(saved_config.get("waterfall_connector_width", 1.0)),
            step=0.5,
            disabled=not connectors,
            key=f"waterfall_connector_width_{plot_id}",
        )
        connector_color = st.color_picker(
            "Connector color",
            value=str(saved_config.get("waterfall_connector_color", "#666666")),
            disabled=not connectors,
            key=f"waterfall_connector_color_{plot_id}",
        )
    with value_column:
        show_values = st.checkbox(
            "Show values on bars",
            value=bool(saved_config.get("waterfall_show_values", True)),
            key=f"waterfall_show_values_{plot_id}",
        )
        number_format = st.text_input(
            "Value format",
            value=str(saved_config.get("waterfall_number_format", ".4g")),
            help="Python number format such as .2f, .3g, or ,.0f.",
            disabled=not show_values,
            key=f"waterfall_number_format_{plot_id}",
        )
        bar_width = st.slider(
            "Bar width",
            min_value=0.2,
            max_value=1.0,
            value=float(saved_config.get("waterfall_bar_width", 0.7)),
            step=0.05,
            key=f"waterfall_bar_width_{plot_id}",
        )
        opacity = st.slider(
            "Bar opacity",
            min_value=0.1,
            max_value=1.0,
            value=float(saved_config.get("waterfall_opacity", 0.9)),
            step=0.05,
            key=f"waterfall_opacity_{plot_id}",
        )

    st.markdown("#### Meaning colors")
    increasing_column, decreasing_column, semantic_total_column = st.columns(3)
    with increasing_column:
        increasing_color = st.color_picker(
            "Increase",
            value=str(saved_config.get("waterfall_increasing_color", "#2ca02c")),
            key=f"waterfall_increasing_color_{plot_id}",
        )
    with decreasing_column:
        decreasing_color = st.color_picker(
            "Decrease",
            value=str(saved_config.get("waterfall_decreasing_color", "#d62728")),
            key=f"waterfall_decreasing_color_{plot_id}",
        )
    with semantic_total_column:
        total_color = st.color_picker(
            "Absolute and total",
            value=str(saved_config.get("waterfall_total_color", "#4c78a8")),
            key=f"waterfall_total_color_{plot_id}",
        )

    return {
        "x": x_column,
        "y": y_column,
        "waterfall_absolute": absolute,
        "waterfall_subtotals": subtotals,
        "waterfall_final_total": final_total,
        "waterfall_total_label": total_label,
        "waterfall_connectors": connectors,
        "waterfall_connector_width": connector_width,
        "waterfall_connector_color": connector_color,
        "waterfall_show_values": show_values,
        "waterfall_number_format": number_format,
        "waterfall_bar_width": bar_width,
        "waterfall_opacity": opacity,
        "waterfall_increasing_color": increasing_color,
        "waterfall_decreasing_color": decreasing_color,
        "waterfall_total_color": total_color,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
