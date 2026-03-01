"""Engine-specific settings component — Plotly/Matplotlib controls.

Extracted from ``BasePlot._render_engine_specific_controls``.
"""

import streamlit as st

from src.web.models.plot_models import PlotConfig
from src.web.rendering.engine_manager import EngineManager


class EngineSettingsComponent:
    """Render controls that depend on the current rendering engine.

    **Plotly mode**: hovermode selector.
    **Matplotlib mode**: LaTeX preamble, TeX system.

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
        st.markdown("---")
        if EngineManager.is_plotly():
            st.markdown("#### :material/interactive_space: Interactive Settings")
            hovermode_options = [
                "x unified",
                "closest",
                "x",
                "y",
                "off",
            ]
            current_hover = saved_config.get("hovermode", "x unified")
            idx = (
                hovermode_options.index(current_hover) if current_hover in hovermode_options else 0
            )
            config["hovermode"] = st.selectbox(
                "Hover mode",
                options=hovermode_options,
                index=idx,
                key=f"hovermode_{self.plot_id}",
                help=("Controls how tooltip information is displayed " "on hover."),
            )
        elif EngineManager.is_matplotlib():
            st.markdown("#### :material/description: LaTeX Settings")
            config["latex_extra_preamble"] = st.text_area(
                "Extra LaTeX preamble",
                value=saved_config.get("latex_extra_preamble", ""),
                key=f"latex_preamble_{self.plot_id}",
                help=("Additional LaTeX preamble commands " "(e.g. \\\\usepackage{...})."),
            )
            tex_options = ["xelatex", "pdflatex", "lualatex"]
            current_tex = saved_config.get("tex_system", "xelatex")
            tex_idx = tex_options.index(current_tex) if current_tex in tex_options else 0
            config["tex_system"] = st.selectbox(
                "TeX system",
                options=tex_options,
                index=tex_idx,
                key=f"tex_system_{self.plot_id}",
                help="TeX compiler to use for LaTeX rendering.",
            )


def render_engine_controls(
    plot_id: int,
    saved_config: PlotConfig,
    config: PlotConfig,
) -> None:
    """Deprecated: use EngineSettingsComponent."""
    EngineSettingsComponent(plot_id, "").render(saved_config, config)
