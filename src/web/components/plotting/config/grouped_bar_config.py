"""Grouped bar plot configuration component."""

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_common_config,
)
from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)
from src.web.models.plot_models import PlotConfig


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a grouped bar plot.

    Extends the common X / Y / title layout with a **Group by** selector
    and X / group filter multi-selects.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary including ``group``, ``x_filter``,
        ``group_filter``, and a ``_needs_advanced`` flag.
    """
    config = render_common_config(data, saved_config, plot_id)

    _numeric_cols, categorical_cols = detect_column_types(data)

    # Group-by selector
    group_default_idx: int = 0
    if saved_config.get("group") and saved_config["group"] in categorical_cols:
        group_default_idx = categorical_cols.index(saved_config["group"])

    group_column: str = st.selectbox(
        "Group by",
        options=categorical_cols,
        index=group_default_idx,
        key=f"group_{plot_id}",
    )

    # X and group filter multi-selects
    x_values, group_values = PlotConfigComponents.render_filter_multiselects(
        data=data,
        x_col=config.get("x"),
        group_col=group_column,
        saved_config=saved_config,
        plot_id=plot_id,
    )

    return {
        **config,
        "group": group_column,
        "color": None,
        "x_filter": x_values,
        "group_filter": group_values,
        "_needs_advanced": True,
    }
