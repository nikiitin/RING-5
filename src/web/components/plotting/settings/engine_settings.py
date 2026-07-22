"""Engine-specific settings component — Plotly/Matplotlib controls.

Extracted from ``BasePlot._render_engine_specific_controls``.
"""

import streamlit as st

from src.web.components.plotting.settings.widget_factory import select_option
from src.web.models.plot_models import PlotConfig
from src.web.rendering.engine_manager import EngineManager


class EngineSettingsComponent:
    """Render controls that depend on the current rendering engine.

    **Plotly mode**: hovermode selector.
    **Matplotlib mode**: secure PGF export settings and TeX system.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier.
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        config: PlotConfig,
    ) -> None:
        """Render engine-specific controls.

        Args:
            saved_config: Previously saved configuration.
            config: Configuration dictionary to populate.
        """
        # [impl->req~ring5.figure.matplotlib-tex-system~1]
        # [impl->req~ring5.figure.plotly-hovermode~1]
        st.markdown("---")
        if EngineManager.is_plotly():
            st.markdown("#### :material/interactive_space: Interactive Settings")
            config["hovermode"] = select_option(
                "Hover mode",
                ["x unified", "closest", "x", "y", "off"],
                saved_config,
                "hovermode",
                self.plot_id,
                widget_key=f"hovermode_{self.plot_id}",
                default="x unified",
                help="Controls how tooltip information is displayed on hover.",
            )
        elif EngineManager.is_matplotlib():
            st.markdown("#### :material/description: LaTeX Settings")
            config["latex_extra_preamble"] = ""
            st.caption(
                "Custom LaTeX preambles are disabled because PGF export treats them as code."
            )
            config["tex_system"] = select_option(
                "TeX system",
                ["xelatex", "pdflatex", "lualatex"],
                saved_config,
                "tex_system",
                self.plot_id,
                widget_key=f"tex_system_{self.plot_id}",
                default="xelatex",
                help="TeX compiler to use for LaTeX rendering.",
            )


def render_engine_controls(
    plot_id: int,
    saved_config: PlotConfig,
    config: PlotConfig,
) -> None:
    """Deprecated: use EngineSettingsComponent."""
    EngineSettingsComponent(plot_id, "").render(saved_config, config)
