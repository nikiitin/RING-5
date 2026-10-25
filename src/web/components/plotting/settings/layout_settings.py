"""Layout settings component — dimensions, margins and grouped-bar geometry.

Usage::

    component = LayoutSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

import pandas as pd
import streamlit as st

from src.web.components.plotting.settings.small_multiples_settings import (
    SmallMultiplesSettingsComponent,
)
from src.web.components.plotting.settings.widget_factory import color_picker, numeric_input, toggle
from src.core.models.plot_config import PlotConfig


class LayoutSettingsComponent:
    """Render layout sizing options (dimensions, margins).

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier (e.g. ``"bar"``, ``"line"``).
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(self, saved_config: PlotConfig, data: pd.DataFrame | None = None) -> PlotConfig:
        """Render layout dimension widgets.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.

        Returns
        -------
        PlotConfig
            Configuration dict with dimension and margin keys.
        """
        # [impl->req~ring5.figure.layout~1]
        st.markdown("**Dimensions**")

        preset_options: dict[str, float] = {
            "Single Column (~3.5in)": 3.5,
            "Double Column (~7.0in)": 7.0,
            "Custom": 0.0,
        }

        default_preset = saved_config.get(
            "document_width_preset",
            "Custom" if "width" in saved_config else "Double Column (~7.0in)",
        )
        preset_idx = (
            list(preset_options.keys()).index(default_preset)
            if default_preset in preset_options
            else 1
        )

        preset: str | None = st.selectbox(
            "Document Size Preset",
            list(preset_options.keys()),
            index=preset_idx,
            key=f"col_preset_{self.plot_id}",
        )
        # Satisfy type checker — selectbox always returns a value here
        if preset is None:
            preset = "Double Column (~7.0in)"

        saved_width = float(
            saved_config.get("width_inches", float(saved_config.get("width", 700)) / 100)
        )
        saved_height = float(
            saved_config.get("height_inches", float(saved_config.get("height", 350)) / 100)
        )
        if saved_width < 0.1 or saved_height < 0.1:
            st.warning(
                "Preview dimensions must be at least 10 pixels (0.1 inches). "
                "Adjust the saved dimensions."
            )
        c1, c2 = st.columns(2)
        with c1:
            if preset == "Custom":
                width_inches = st.number_input(
                    "Width (inches)",
                    min_value=0.1,
                    value=max(0.1, saved_width),
                    step=0.5,
                    key=f"wi_{self.plot_id}",
                )
            else:
                width_inches = preset_options[preset]
                st.number_input(
                    "Width (inches)",
                    value=width_inches,
                    disabled=True,
                    key=f"wi_disabled_{self.plot_id}",
                )

        with c2:
            height_inches = st.number_input(
                "Height (inches)",
                min_value=0.1,
                value=max(0.1, saved_height),
                step=0.5,
                key=f"hi_{self.plot_id}",
            )

        # Plotly expects pixels — scale 1 inch → 100 px for preview.
        width = round(width_inches * 100)
        height = round(height_inches * 100)

        config: PlotConfig = {
            "document_width_preset": preset,
            "width_inches": width_inches,
            "height_inches": height_inches,
            "width": width,
            "height": height,
            "margin_l": saved_config.get("margin_l", 0),
            "margin_r": saved_config.get("margin_r", 0),
            "margin_t": saved_config.get("margin_t", 0),
            "margin_b": saved_config.get("margin_b", 0),
            "margin_pad": saved_config.get("margin_pad", 0),
            "automargin": saved_config.get("automargin", True),
        }
        if self.plot_type in {"grouped_bar", "grouped_stacked_bar"}:
            config.update(self._render_grouped_bars(saved_config))
        if data is not None:
            config.update(SmallMultiplesSettingsComponent(self.plot_id).render(saved_config, data))
        return config

    def _render_grouped_bars(self, saved_config: PlotConfig) -> PlotConfig:
        """Expose the existing grouped-bar boundaries, shading and isolation."""
        # [impl->req~ring5.figure.alternate-category-shading~1]
        st.markdown("#### Grouped Bar Layout")
        config: PlotConfig = {}
        left, right = st.columns(2)
        with left:
            config["show_separators"] = toggle(
                "Show Vertical Separators",
                saved_config,
                "show_separators",
                self.plot_id,
            )
            config["separator_color"] = color_picker(
                "Separator Color",
                saved_config,
                "separator_color",
                self.plot_id,
                default="#E0E0E0",
            )
        with right:
            config["shade_alternate"] = toggle(
                "Shade Alternate Groups",
                saved_config,
                "shade_alternate",
                self.plot_id,
            )
            config["shade_color"] = color_picker(
                "Group Shade Color",
                saved_config,
                "shade_color",
                self.plot_id,
                default="#F5F5F5",
            )
        config["isolate_last_group"] = toggle(
            "Isolate Last Group",
            saved_config,
            "isolate_last_group",
            self.plot_id,
            help="Add space and a boundary before the last category.",
        )
        if config["isolate_last_group"]:
            config["isolation_gap"] = numeric_input(
                "Isolation Gap Size",
                saved_config,
                "isolation_gap",
                self.plot_id,
                default=0.5,
                min_value=0.0,
                step=0.1,
            )
        return config
