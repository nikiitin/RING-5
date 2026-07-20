"""Human-first controls for splitting one plot into comparable panels."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.models.plot_models import PlotConfig


class SmallMultiplesSettingsComponent:
    """Render opt-in facet controls inside the Layout settings section."""

    def __init__(self, plot_id: int) -> None:
        self.plot_id = plot_id

    def render(self, saved_config: PlotConfig, data: pd.DataFrame | None) -> PlotConfig:
        # [impl->req~ring5.plots.small-multiples~1]
        """Return serializable small-multiples settings for the active plot."""
        st.markdown("**Small multiples**")
        enabled = st.toggle(
            "Split this plot into comparable panels",
            value=bool(saved_config.get("small_multiples_enabled", False)),
            key=f"small_multiples_enabled_{self.plot_id}",
            help="Repeat this plot for each category while keeping its styling and scales aligned.",
        )
        config: PlotConfig = {"small_multiples_enabled": enabled}
        if not enabled:
            return config
        if data is None:
            st.info("Process plot data before choosing facet columns.")
            return config

        categorical = data.select_dtypes(
            include=["object", "string", "category", "bool"]
        ).columns.tolist()
        if not categorical:
            st.info("This plot has no categorical columns available for panels.")
            return config

        saved_columns = [
            str(column)
            for column in saved_config.get("small_multiples_by", [])
            if str(column) in categorical
        ]
        by = st.multiselect(
            "Create one panel for each combination of",
            options=categorical,
            default=saved_columns,
            key=f"small_multiples_by_{self.plot_id}",
            help=(
                "Choose columns from broadest to most specific; their values form each panel label."
            ),
        )
        config["small_multiples_by"] = by
        if not by:
            st.caption("Choose at least one categorical column to build the panels.")
            return config

        panel_count = len(data.loc[:, by].drop_duplicates())
        if panel_count < 2:
            st.warning("These columns currently produce only one panel. Choose another category.")
        elif panel_count > 24:
            st.warning(
                f"This creates {panel_count} panels. Consider a filter or broader category first."
            )
        else:
            st.caption(f"{panel_count} panels, ordered by their first appearance in the data.")

        max_columns = max(1, min(6, panel_count))
        saved_grid_columns = int(saved_config.get("small_multiples_columns", min(3, max_columns)))
        grid_columns = st.number_input(
            "Panels per row",
            min_value=1,
            max_value=max_columns,
            value=min(max(1, saved_grid_columns), max_columns),
            step=1,
            key=f"small_multiples_columns_{self.plot_id}",
        )
        config["small_multiples_columns"] = int(grid_columns)

        c1, c2, c3 = st.columns(3)
        with c1:
            config["small_multiples_shared_xaxes"] = st.checkbox(
                "Share X scale",
                value=bool(saved_config.get("small_multiples_shared_xaxes", True)),
                key=f"small_multiples_shared_x_{self.plot_id}",
            )
        with c2:
            config["small_multiples_shared_yaxes"] = st.checkbox(
                "Share Y scale",
                value=bool(saved_config.get("small_multiples_shared_yaxes", True)),
                key=f"small_multiples_shared_y_{self.plot_id}",
            )
        with c3:
            config["small_multiples_shared_legend"] = st.checkbox(
                "One legend",
                value=bool(saved_config.get("small_multiples_shared_legend", True)),
                key=f"small_multiples_shared_legend_{self.plot_id}",
            )
        config["small_multiples_panel_height"] = int(
            st.number_input(
                "Panel row height (pixels)",
                min_value=180,
                max_value=800,
                value=int(saved_config.get("small_multiples_panel_height", 320)),
                step=20,
                key=f"small_multiples_panel_height_{self.plot_id}",
            )
        )
        return config


__all__ = ["SmallMultiplesSettingsComponent"]
