"""Layout settings component — dimensions and margin configuration.

Extracted from ``BaseStyleUI.render_layout_options()`` as a standalone
component following the component-only architecture (P1, P9).

Usage::

    component = LayoutSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

import streamlit as st

from src.web.models.plot_models import PlotConfig


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

    def render(self, saved_config: PlotConfig) -> PlotConfig:
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

        default_preset = saved_config.get("document_width_preset", "Double Column (~7.0in)")
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

        c1, c2 = st.columns(2)
        with c1:
            if preset == "Custom":
                width_inches = st.number_input(
                    "Width (inches)",
                    min_value=1.0,
                    max_value=30.0,
                    value=float(saved_config.get("width_inches", 7.0)),
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
                min_value=1.0,
                max_value=30.0,
                value=float(saved_config.get("height_inches", 3.5)),
                step=0.5,
                key=f"hi_{self.plot_id}",
            )

        # Plotly expects pixels — scale 1 inch → 100 px for preview.
        width = int(width_inches * 100)
        height = int(height_inches * 100)

        return {
            "document_width_preset": preset,
            "width_inches": width_inches,
            "height_inches": height_inches,
            "width": width,
            "height": height,
            "margin_l": 0,
            "margin_r": 0,
            "margin_t": 0,
            "margin_b": 0,
            "margin_pad": 0,
            "automargin": True,
        }
