"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.models.data_models import PipelineStep
from src.core.models.plot_config import ShapeConfig
from src.core.models.visualization.palettes import (
    PALETTE_REGISTRY,
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.services.plot_interaction_service import (
    resolve_item_order,
    try_float,
    try_float_edit,
    update_config_from_relayout,
)
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.styles import StyleManager
from src.web.rendering.engine_manager import EngineManager


class BasePlot(ABC):
    """Abstract base class for all plot types."""

    def __init__(self, plot_id: int, name: str, plot_type: str) -> None:
        """
        Initialize base plot.

        Args:
            plot_id: Unique identifier for the plot
            name: Display name for the plot
            plot_type: Type of plot (bar, line, etc.)
        """
        self.plot_id: int = plot_id
        self.name: str = name
        self.plot_type: str = plot_type
        self.config: PlotConfig = {}
        self.processed_data: pd.DataFrame | None = None
        self.last_generated_fig: go.Figure | None = None
        self.last_traces: TraceBuildResult | None = None
        self.pipeline: list[PipelineStep] = []
        self.pipeline_counter: int = 0
        self.legend_mappings_by_column: dict[str, dict[str, str]] = {}
        self.legend_mappings: dict[str, str] = {}

        # Initialize Style Manager
        self.style_manager: StyleManager = StyleManager(self.plot_id, self.plot_type)

    @abstractmethod
    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """
        Render the configuration UI for this plot type.

        Args:
            data: The processed data to plot
            saved_config: Previously saved configuration

        Returns:
            Current configuration dictionary
        """

    @abstractmethod
    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """
        Produce engine-agnostic trace data from *data* and *config*.

        Each concrete plot type implements this to output
        ``TraceBuildResult`` containing ``List[TraceConfig]`` plus
        any auxiliary layout metadata (barmode, shapes, annotations).

        Args:
            data: The processed data to plot.
            config: Configuration dictionary.

        Returns:
            ``TraceBuildResult`` with traces and metadata.
        """

    def create_figure(self, data: pd.DataFrame, config: dict[str, Any]) -> go.Figure:
        """
        Create the Plotly figure from data and configuration.

        Delegates to ``create_traces()`` and converts the result
        to a ``go.Figure`` via the trace-to-plotly converter.

        Args:
            data: The data to plot.
            config: Configuration dictionary.

        Returns:
            Plotly Figure object.
        """
        from src.web.rendering.trace_to_plotly import traces_to_plotly

        result = self.create_traces(data, config)
        self.last_traces = result
        fig = traces_to_plotly(result)

        # Show a placeholder message when no traces were produced
        # (e.g. the user has not selected X / Y columns yet).
        if not result.traces:
            fig.update_layout(title_text="Please select at least one X and one Y column.")

        return fig

    def update_from_relayout(self, relayout_data: dict[str, Any]) -> bool:
        """
        Update config from client-side relayout data (zoom/pan, legend drag).

        Delegates pure computation to update_config_from_relayout (Layer B).

        Args:
            relayout_data: Dictionary of relayout events from Plotly

        Returns:
            True if config changed, False otherwise
        """
        updated_config, changed = update_config_from_relayout(self.config, relayout_data)

        if changed:
            self.config = updated_config
            self.last_generated_fig = None

        return changed

    @abstractmethod
    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """
        Get the column name used for legend/color coding.

        Args:
            config: Configuration dictionary

        Returns:
            Column name or None
        """

    def apply_legend_labels(
        self, fig: go.Figure, legend_labels: dict[str, str] | None
    ) -> go.Figure:
        """
        Apply custom legend labels to the figure.

        Args:
            fig: Plotly figure
            legend_labels: Mapping of original labels to custom labels

        Returns:
            Updated figure
        """
        if legend_labels:
            fig.for_each_trace(
                lambda t: t.update(  # type: ignore[attr-defined]
                    name=legend_labels.get(t.name, t.name)  # type: ignore[attr-defined]
                )
            )
        return fig

    def apply_common_layout(self, fig: go.Figure, config: dict[str, Any]) -> go.Figure:
        """
        Apply common layout settings.
        Delegates to StyleManager.
        """
        return self.style_manager.apply_styles(fig, config)

    def generate_figure(self) -> go.Figure:
        """
        Generate and cache the final Plotly figure.

        Calls create_figure → apply_common_layout → legend labels.
        """
        if self.processed_data is None:
            raise ValueError(f"Plot '{self.name}' has no processed data.")

        fig = self.create_figure(self.processed_data, self.config)
        fig = self.apply_common_layout(fig, self.config)
        legend_labels: dict[str, str] | None = self.config.get("legend_labels")
        if legend_labels:
            fig.for_each_trace(
                lambda t: t.update(  # type: ignore[attr-defined]
                    name=legend_labels.get(t.name, t.name)  # type: ignore[attr-defined]
                )
            )

        self.last_generated_fig = fig
        return fig

    def to_dict(self) -> dict[str, Any]:
        """
        Convert plot to dictionary for serialization.

        Returns:
            Dictionary representation (without Figure objects)
        """
        return {
            "id": self.plot_id,
            "name": self.name,
            "plot_type": self.plot_type,
            "config": self.config,
            "processed_data": (
                self.processed_data.to_csv(index=False)
                if isinstance(self.processed_data, pd.DataFrame)
                else None
            ),
            "pipeline": self.pipeline,
            "pipeline_counter": self.pipeline_counter,
            "legend_mappings_by_column": self.legend_mappings_by_column,
            "legend_mappings": self.legend_mappings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasePlot":
        """
        Create plot instance from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Plot instance
        """
        # Import here to avoid circular imports
        from .plot_factory import PlotFactory

        plot = PlotFactory.create_plot(
            plot_type=data["plot_type"], plot_id=data["id"], name=data["name"]
        )

        plot.config = data.get("config", {})
        plot.pipeline = data.get("pipeline", [])
        plot.pipeline_counter = data.get("pipeline_counter", 0)
        plot.legend_mappings_by_column = data.get("legend_mappings_by_column", {})
        plot.legend_mappings = data.get("legend_mappings", {})

        # Deserialize processed_data if it exists
        if data.get("processed_data"):
            plot.processed_data = pd.read_csv(StringIO(data["processed_data"]))

        return plot

    def render_common_config(
        self, data: pd.DataFrame, saved_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Render common configuration options.

        Args:
            data: The data to plot
            saved_config: Previously saved configuration

        Returns:
            Configuration dictionary with common options
        """
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        col1, col2 = st.columns(2)

        with col1:
            # X-axis
            x_default_idx = 0
            if saved_config.get("x") and saved_config["x"] in (categorical_cols + numeric_cols):
                x_default_idx = (categorical_cols + numeric_cols).index(saved_config["x"])

            x_column = st.selectbox(
                "X-axis",
                options=categorical_cols + numeric_cols,
                index=x_default_idx,
                key=f"x_{self.plot_id}",
            )

            # Y-axis
            y_default_idx = 0
            if saved_config.get("y") and saved_config["y"] in numeric_cols:
                y_default_idx = numeric_cols.index(saved_config["y"])

            y_column = st.selectbox(
                "Y-axis", options=numeric_cols, index=y_default_idx, key=f"y_{self.plot_id}"
            )

        with col2:
            # Title & Labels
            default_title = saved_config.get("title", f"{y_column} by {x_column}") or ""
            default_xlabel: str = str(saved_config.get("xlabel", x_column) or "")
            default_ylabel: str = str(saved_config.get("ylabel", y_column) or "")
            default_legend_title: str = str(saved_config.get("legend_title", "") or "")

            from src.web.pages.ui.components.plot_config_components import (
                PlotConfigComponents,
            )

            label_config = PlotConfigComponents.render_title_labels_section(
                saved_config=saved_config,
                plot_id=self.plot_id,
                default_title=default_title,
                default_xlabel=default_xlabel,
                default_ylabel=default_ylabel,
                include_legend_title=True,
                default_legend_title=default_legend_title,
            )
            title = label_config["title"]
            xlabel = label_config["xlabel"]
            ylabel = label_config["ylabel"]
            legend_title = label_config["legend_title"]

        return {
            "x": x_column,
            "y": y_column,
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "legend_title": legend_title,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
        }

    def render_display_options(self, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render sizing and layout options via StyleManager."""
        return self.style_manager.render_layout_options(saved_config)

    def render_theme_options(
        self, saved_config: dict[str, Any], items: list[str] | None = None
    ) -> dict[str, Any]:
        """Render theme options via StyleManager."""
        # Pass data for potential data-dependent theming (e.g. series colors)
        # Use a prefix to distinguish from advanced options
        return self.style_manager.render_theme_options(
            saved_config, self.processed_data, items=items, key_prefix="theme_"
        )

    # ------------------------------------------------------------------
    # Pills-driven section dispatcher
    # ------------------------------------------------------------------

    def render_settings_section(
        self,
        section: str | None,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Render UI for a single settings section selected via pills.

        Each pill maps to one or more existing rendering methods so that
        all widget ``key`` values are preserved exactly.

        Args:
            section: The key returned by ``render_settings_pills``
                (``None`` when nothing is selected).
            saved_config: Current configuration dictionary.
            data: Processed data for data-dependent widgets.

        Returns:
            Configuration dictionary produced by the selected section.
        """
        if section is None:
            return {}

        dispatch = {
            "layout": self._section_layout,
            "typography": self._section_typography,
            "legends": self._section_legends,
            "axes": self._section_axes,
            "data_labels": self._section_data_labels,
            "colors": self._section_colors,
            "advanced": self._section_advanced,
        }
        handler = dispatch.get(section)
        if handler is None:
            return {}
        return handler(saved_config, data)

    # -- individual section helpers ---

    def _section_layout(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        return self.render_display_options(saved_config)

    def _section_typography(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        return self.style_manager.ui_manager._render_typography_section(
            saved_config, key_prefix="theme_"
        )

    def _section_legends(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        _LEGEND_LABELS: dict[str, str] = {
            "primary": ":material/legend_toggle: Primary",
            "secondary": ":material/legend_toggle: Secondary",
            "boxed": ":material/legend_toggle: Boxed",
        }
        legend_tab: str | None = st.pills(
            "Legend",
            options=list(_LEGEND_LABELS.keys()),
            format_func=lambda x: _LEGEND_LABELS.get(x, str(x)),
            selection_mode="single",
            key=f"legend_nav_{self.plot_id}",
            default="primary",
        )
        prefix_map = {
            "primary": "theme_",
            "secondary": "legend2_",
            "boxed": "legend3_",
        }
        prefix = prefix_map.get(legend_tab or "primary", "theme_")
        return self.style_manager.ui_manager._render_legend_section(saved_config, key_prefix=prefix)

    def _section_axes(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        _AXIS_LABELS: dict[str, str] = {
            "x": ":material/straighten: X-Axis",
            "y_left": ":material/straighten: Y-Left",
            "y_right": ":material/straighten: Y-Right",
        }
        axis_tab: str | None = st.pills(
            "Axis",
            options=list(_AXIS_LABELS.keys()),
            format_func=lambda x: _AXIS_LABELS.get(x, str(x)),
            selection_mode="single",
            key=f"axis_nav_{self.plot_id}",
            default="x",
        )
        config: dict[str, Any] = {}
        if axis_tab == "x" or axis_tab is None:
            self._render_x_axis_settings(saved_config, config)
            specific = self.render_specific_advanced_options(saved_config, data)
            config.update(specific)
            config["xaxis_labels"] = self.style_manager.render_xaxis_labels_ui(saved_config, data)
            if data is not None:
                self._render_ordering_ui(saved_config, data, config)
        elif axis_tab == "y_left":
            self._render_y_axis_settings(saved_config, config, prefix="")
        elif axis_tab == "y_right":
            self._render_y_axis_settings(saved_config, config, prefix="y2")
        return config

    def _render_x_axis_settings(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render X-axis specific settings (tick angle)."""
        st.markdown("#### X-Axis Settings")
        config["xaxis_tickangle"] = st.slider(
            "X-axis Label Rotation",
            min_value=-90,
            max_value=90,
            value=saved_config.get("xaxis_tickangle", -45),
            step=15,
            key=f"xaxis_angle_{self.plot_id}",
            help="Rotate X-axis labels to prevent overlap",
        )

    def _render_y_axis_settings(
        self,
        saved_config: dict[str, Any],
        config: dict[str, Any],
        prefix: str,
    ) -> None:
        """Render Y-axis settings for left or right axis.

        Args:
            saved_config: Previously saved configuration.
            config: Current configuration to update.
            prefix: Empty string for left axis, ``"y2"`` for right axis.
        """
        label = "Y-Left Axis" if not prefix else "Y-Right Axis"
        st.markdown(f"#### {label} Settings")

        dtick_key = f"{prefix}yaxis_dtick" if prefix else "yaxis_dtick"
        dtick: float = st.number_input(
            f"{label} Step Size (0 for auto)",
            min_value=0.0,
            value=float(saved_config.get(dtick_key) or 0.0),
            key=f"{prefix}ydtick_{self.plot_id}",
        )
        if dtick > 0:
            config[dtick_key] = dtick

    def _section_data_labels(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        dl = self.style_manager.render_data_labels_ui(saved_config, key_prefix="theme_")
        return {
            "show_values": dl.get("show_values", False),
            "text_color_mode": dl.get("text_color_mode"),
            "text_color": dl.get("text_color"),
            "text_font_size": dl.get("text_font_size"),
            "text_rotation": dl.get("text_rotation"),
            "text_position": dl.get("text_position"),
            "text_anchor": dl.get("text_anchor"),
            "text_format": dl.get("text_format"),
            "text_display_logic": dl.get("text_display_logic"),
            "text_threshold": dl.get("text_threshold"),
            "text_constraint": dl.get("text_constraint"),
        }

    def _section_colors(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        """Unified palette selector using core PALETTE_REGISTRY."""
        st.markdown("#### :material/palette: Color Palette")
        palette_names = get_palette_names()
        current_palette = saved_config.get("color_palette", "wong")
        # Accept either a string name or the list itself
        if isinstance(current_palette, list):
            # Reverse-lookup: find matching palette name
            current_palette = "wong"
            for name, colors in PALETTE_REGISTRY.items():
                if colors == saved_config.get("color_palette"):
                    current_palette = name
                    break
        idx = palette_names.index(current_palette) if current_palette in palette_names else 0

        def _fmt_palette(name: str) -> str:
            label = name.replace("_", " ").title()
            if is_colorblind_safe(name):
                label = f"\u2713 {label}"
            return label

        selected_palette: str = st.selectbox(
            "Palette",
            options=palette_names,
            index=idx,
            format_func=_fmt_palette,
            key=f"palette_select_{self.plot_id}",
            help="Palettes marked \u2713 are colorblind-safe. Wong (default) is recommended.",
        )
        palette_colors = resolve_palette(selected_palette)
        # Preview swatches
        swatch_html = " ".join(
            f'<span style="display:inline-block;width:20px;height:20px;'
            f"background:{c};border:1px solid #ccc;border-radius:3px;"
            f'margin-right:2px;"></span>'
            for c in palette_colors
        )
        st.markdown(swatch_html, unsafe_allow_html=True)
        config: dict[str, Any] = {"color_palette": selected_palette}

        st.markdown("---")
        series = self.style_manager.ui_manager._render_series_section(
            saved_config,
            data,
            items=None,
            key_prefix="theme_",
            palette_name=selected_palette,
        )
        st.markdown("---")
        bg = self.style_manager.ui_manager._render_backgrounds_section(
            saved_config, key_prefix="theme_"
        )
        config.update(series)
        config.update(bg)
        return config

    def _section_advanced(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        config: dict[str, Any] = {}

        # ── Export & Download ────────────────────────────────────
        st.markdown("#### Export & Download")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            config["show_error_bars"] = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )
        with col_exp2:
            download_formats: list[str] = ["html", "png", "pdf", "svg"]
            default_fmt_idx: int = 0
            if saved_config.get("download_format") in download_formats:
                default_fmt_idx = download_formats.index(
                    saved_config["download_format"]
                )
            config["download_format"] = st.selectbox(
                "Default Download Format",
                options=download_formats,
                index=default_fmt_idx,
                key=f"download_fmt_{self.plot_id}",
            )
            config["export_scale"] = st.selectbox(
                "Download Scale (Resolution)",
                options=[1, 2, 3],
                index=[1, 2, 3].index(saved_config.get("export_scale", 1)),
                key=f"exp_scale_{self.plot_id}",
                help="1x = Screen. 3x = High Res (Publication).",
            )
            w: int = saved_config.get("width", 800)
            h: int = saved_config.get("height", 500)
            s: int = config["export_scale"]
            st.caption(f"Download Size: {w * s} x {h * s} px")

        # ── Legend & Interactivity ───────────────────────────────
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help="Allows you to drag the legend/title and click to edit text directly on the plot.",
        )

        # Series Renaming
        if st.checkbox(
            "Show Series Renaming", value=False, key=f"show_series_style_{self.plot_id}"
        ):
            st.markdown("#### Rename Series")
            with st.expander("Rename Items", expanded=True):
                renaming_styles = self.style_manager.render_series_renaming_ui(saved_config, data)
                if "series_styles" not in config:
                    config["series_styles"] = {}
                for k, v in renaming_styles.items():
                    if k not in config["series_styles"]:
                        config["series_styles"][k] = v
                    else:
                        config["series_styles"][k].update(v)
        else:
            if "series_styles" not in config:
                config["series_styles"] = saved_config.get("series_styles", {})

        # Reference Line
        self._render_reference_line_ui(saved_config, data, config)

        # Annotations (Shapes)
        st.markdown("#### Annotations (Shapes)")
        config["shapes"] = self._render_shapes_ui(saved_config)

        # ── Engine-specific controls (Step 30) ──
        self._render_engine_specific_controls(saved_config, config)

        return config

    def _render_engine_specific_controls(
        self,
        saved_config: dict[str, Any],
        config: dict[str, Any],
    ) -> None:
        """Render controls that depend on the current engine mode.

        **Plotly mode**: hovermode selector.
        **Matplotlib mode**: LaTeX preamble, TeX system.
        """
        st.markdown("---")
        if EngineManager.is_plotly():
            st.markdown("#### :material/interactive_space: Interactive Settings")
            hovermode_options = ["x unified", "closest", "x", "y", "off"]
            current_hover = saved_config.get("hovermode", "x unified")
            idx = (
                hovermode_options.index(current_hover) if current_hover in hovermode_options else 0
            )
            config["hovermode"] = st.selectbox(
                "Hover mode",
                options=hovermode_options,
                index=idx,
                key=f"hovermode_{self.plot_id}",
                help="Controls how tooltip information is displayed on hover.",
            )
        elif EngineManager.is_matplotlib():
            st.markdown("#### :material/description: LaTeX Settings")
            config["latex_extra_preamble"] = st.text_area(
                "Extra LaTeX preamble",
                value=saved_config.get("latex_extra_preamble", ""),
                key=f"latex_preamble_{self.plot_id}",
                help="Additional LaTeX preamble commands (e.g. \\\\usepackage{...}).",
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

    def render_advanced_options(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """
        Render advanced options (legend, error bars, download format, axis settings).
        Should be called within an expander.

        Args:
            saved_config: Previously saved configuration
            data: The data being plotted (optional, needed for ordering options)

        Returns:
            Configuration dictionary with advanced options
        """
        config: dict[str, Any] = {}

        # 1. General & Axis Settings
        self._render_general_settings(saved_config, config)

        # 2. Specific Settings (Plot Type Specific)
        specific_config = self.render_specific_advanced_options(saved_config, data)
        config.update(specific_config)

        # 3. Label Renaming (Generic X-axis renames mostly)
        config["xaxis_labels"] = self.style_manager.render_xaxis_labels_ui(saved_config, data)

        # 4. Ordering Control
        if data is not None:
            self._render_ordering_ui(saved_config, data, config)

        # 5. Legend & Interactivity
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help="Allows you to drag the legend/title and click to edit text directly on the plot.",
        )

        # 6. Series Styling (Color, Shape, Pattern, Name)
        if st.checkbox(
            "Show Series Renaming", value=False, key=f"show_series_style_{self.plot_id}"
        ):
            st.markdown("#### Rename Series")
            with st.expander("Rename Items", expanded=True):
                # Colors are now handled in Style & Theme, so we only do Renaming here.
                renaming_styles = self.style_manager.render_series_renaming_ui(saved_config, data)
                # Merge with existing styles (which might have colors from Style Menu)
                if "series_styles" not in config:
                    config["series_styles"] = {}

                # Deep update of series styles
                # series_styles is Dict[str, Dict].
                for k, v in renaming_styles.items():
                    if k not in config["series_styles"]:
                        config["series_styles"][k] = v
                    else:
                        config["series_styles"][k].update(v)
        else:
            # Preserve existing series styles if UI is hidden
            if "series_styles" not in config:
                config["series_styles"] = saved_config.get("series_styles", {})

        # 7. Reference Line (Normalizer)
        self._render_reference_line_ui(saved_config, data, config)

        # 8. Annotations
        st.markdown("#### Annotations (Shapes)")
        config["shapes"] = self._render_shapes_ui(saved_config)

        return config

    def render_specific_advanced_options(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """
        Hook for subclasses to render plot-specific advanced options.
        Default implementation renders Bar settings if plot_type contains 'bar'.
        """
        config = {}
        if "bar" in self.plot_type:
            st.markdown("#### Bar Settings")
            col_bar1, col_bar2 = st.columns(2)
            with col_bar1:
                config["bargap"] = st.slider(
                    "Spacing between Bars (Gap)",
                    min_value=0.0,
                    max_value=1.0,
                    value=saved_config.get("bargap", 0.2),
                    step=0.05,
                    key=f"bargap_{self.plot_id}",
                )

            with col_bar2:
                if "grouped" in self.plot_type:
                    config["bargroupgap"] = st.slider(
                        "Spacing between Groups",
                        min_value=0.0,
                        max_value=1.0,
                        value=saved_config.get("bargroupgap", 0.0),
                        step=0.05,
                        key=f"bargroupgap_{self.plot_id}",
                    )

                if "stacked" in self.plot_type:
                    config["bar_border_width"] = st.slider(
                        "Bar Border Width",
                        min_value=0.0,
                        max_value=5.0,
                        value=saved_config.get("bar_border_width", 0.0),
                        step=0.5,
                        key=f"bar_border_{self.plot_id}",
                        help="Adds a white border around each bar segment to separate stacked items.",
                    )
        return config

    def _render_general_settings(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Helper to render general settings.

        Args:
            saved_config: Previously saved configuration
            config: Current configuration to update
        """
        st.markdown("#### General & Axis")
        col1, col2 = st.columns(2)
        with col1:
            config["show_error_bars"] = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )

            # Y-axis Stepping
            dtick: float = st.number_input(
                "Y-axis Step Size (0 for auto)",
                min_value=0.0,
                value=float(saved_config.get("yaxis_dtick") or 0.0),
                key=f"ydtick_{self.plot_id}",
            )
            if dtick > 0:
                config["yaxis_dtick"] = dtick

        with col2:
            download_formats: list[str] = ["html", "png", "pdf", "svg"]
            default_fmt_idx: int = 0
            if saved_config.get("download_format") in download_formats:
                default_fmt_idx = download_formats.index(saved_config["download_format"])

            config["download_format"] = st.selectbox(
                "Default Download Format",
                options=download_formats,
                index=default_fmt_idx,
                key=f"download_fmt_{self.plot_id}",
            )

            # Download Scale
            config["export_scale"] = st.selectbox(
                "Download Scale (Resolution)",
                options=[1, 2, 3],
                index=[1, 2, 3].index(saved_config.get("export_scale", 1)),
                key=f"exp_scale_{self.plot_id}",
                help="1x = Screen Resolution (WYSIWYG). 3x = High Res (Publication).",
            )

            # Dimension Preview
            w: int = saved_config.get("width", 800)
            h: int = saved_config.get("height", 500)
            s: int = config["export_scale"]
            st.caption(f"Download Size: {w * s} x {h * s} px")
            st.caption("Change base dimensions in 'Layout' settings.")

            config["xaxis_tickangle"] = st.slider(
                "X-axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=saved_config.get("xaxis_tickangle", -45),
                step=15,
                key=f"xaxis_angle_{self.plot_id}",
                help="Rotate X-axis labels to prevent overlap",
            )

    def _render_ordering_ui(
        self, saved_config: dict[str, Any], data: pd.DataFrame, config: dict[str, Any]
    ) -> None:
        """Helper to render ordering UI.

        Args:
            saved_config: Previously saved configuration
            data: Data being plotted
            config: Current configuration to update
        """
        st.markdown("#### Ordering Control")

        # X-axis Order
        if saved_config.get("x") and saved_config["x"] in data.columns:
            with st.expander("Reorder and Rename X-axis Labels"):
                unique_x: list[str] = sorted(data[saved_config["x"]].unique().tolist())
                x_result = self.render_reorderable_list(
                    "X-axis Order",
                    unique_x,
                    "xaxis",
                    default_order=saved_config.get("xaxis_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("xaxis_labels"),
                )
                order_x, renames_x = x_result  # type: ignore[misc]
                config["xaxis_order"] = order_x
                if renames_x:
                    config["xaxis_labels"] = renames_x

        # Group Order
        if saved_config.get("group") and saved_config["group"] in data.columns:
            with st.expander("Reorder and Rename Groups"):
                unique_g: list[str] = sorted(data[saved_config["group"]].unique().tolist())
                g_result = self.render_reorderable_list(
                    "Group Order",
                    unique_g,
                    "group",
                    legend_labels=saved_config.get("legend_labels"),
                    default_order=saved_config.get("group_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("legend_labels"),
                )
                order_g, renames_g = g_result  # type: ignore[misc]
                config["group_order"] = order_g
                if renames_g:
                    config["legend_labels"] = renames_g

        # Legend Order (Color)
        if saved_config.get("color") and saved_config["color"] in data.columns:
            with st.expander("Reorder and Rename Legend Items"):
                unique_c: list[str] = sorted(data[saved_config["color"]].unique().tolist())
                c_result = self.render_reorderable_list(
                    "Legend Order",
                    unique_c,
                    "legend",
                    legend_labels=saved_config.get("legend_labels"),
                    default_order=saved_config.get("legend_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("legend_labels"),
                )
                order_c, renames_c = c_result  # type: ignore[misc]
                config["legend_order"] = order_c
                if renames_c:
                    if "legend_labels" not in config:
                        config["legend_labels"] = {}
                    config["legend_labels"].update(renames_c)

    def _render_shapes_ui(self, saved_config: dict[str, Any]) -> list[ShapeConfig]:
        """Helper to render Shapes UI.

        Args:
            saved_config: Previously saved configuration

        Returns:
            List of shape configuration dictionaries
        """
        shapes: list[ShapeConfig] = saved_config.get("shapes", [])

        # Add new shape
        with st.expander("Add New Shape"):
            new_shape_type: str = st.selectbox(
                "Type", ["line", "circle", "rect"], key=f"new_shape_type_{self.plot_id}"
            )
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                x0: str = st.text_input("x0", key=f"s_x0_{self.plot_id}")
            with c2:
                y0: str = st.text_input("y0", key=f"s_y0_{self.plot_id}")
            with c3:
                x1: str = st.text_input("x1", key=f"s_x1_{self.plot_id}")
            with c4:
                y1: str = st.text_input("y1", key=f"s_y1_{self.plot_id}")

            c5, c6 = st.columns(2)
            with c5:
                s_color: str = st.color_picker("Color", "#000000", key=f"s_color_{self.plot_id}")
            with c6:
                s_width: int = st.number_input("Width", 1, 10, 2, key=f"s_width_{self.plot_id}")

            if st.button("Add Shape", key=f"add_shape_{self.plot_id}"):
                shapes.append(
                    {
                        "type": new_shape_type,
                        "x0": try_float(x0),
                        "y0": try_float(y0),
                        "x1": try_float(x1),
                        "y1": try_float(y1),
                        "line": {"color": s_color, "width": s_width},
                    }
                )
                st.rerun()

        # List existing shapes
        if shapes:
            st.markdown("**Existing Shapes (Edit to Resize):**")

            h1, h2, h3, h4, h5, h6 = st.columns([1, 1, 1, 1, 1, 0.5])
            with h1:
                st.caption("x0")
            with h2:
                st.caption("y0")
            with h3:
                st.caption("x1")
            with h4:
                st.caption("y1")
            with h5:
                st.caption("Type")

        # Helper function: uses imported try_float_edit from plot_interaction_service

        if st.session_state.get(f"edit_shapes_{self.plot_id}", False):
            for i, shape in enumerate(shapes):
                c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 0.5])

                with c1:
                    new_x0: str = st.text_input(
                        "x0",
                        value=str(shape["x0"]),
                        key=f"edit_x0_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c2:
                    new_y0: str = st.text_input(
                        "y0",
                        value=str(shape["y0"]),
                        key=f"edit_y0_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c3:
                    new_x1: str = st.text_input(
                        "x1",
                        value=str(shape["x1"]),
                        key=f"edit_x1_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c4:
                    new_y1: str = st.text_input(
                        "y1",
                        value=str(shape["y1"]),
                        key=f"edit_y1_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c5:
                    st.text(shape["type"])
                with c6:
                    if st.button("🗑️", key=f"del_shape_{i}_{self.plot_id}"):
                        shapes.pop(i)
                        st.rerun()

                shape["x0"] = try_float_edit(new_x0)
                shape["y0"] = try_float_edit(new_y0)
                shape["x1"] = try_float_edit(new_x1)
                shape["y1"] = try_float_edit(new_y1)

        return shapes

    def render_reorderable_list(
        self,
        label: str,
        items: list[str],
        key_prefix: str,
        legend_labels: dict[str, str] | None = None,
        default_order: list[str] | None = None,
        enable_rename: bool = False,
        rename_map: dict[str, str] | None = None,
    ) -> list[str] | tuple[list[str], dict[str, str]]:
        """
        Render a list that can be reordered using up/down buttons.

        When *enable_rename* is ``True`` the item label is rendered as
        an editable text input and the method returns a tuple
        ``(order, renames)`` instead of just the order list.

        Args:
            label: Display label for the list
            items: List of items to reorder
            key_prefix: Prefix for session state keys
            legend_labels: Optional mapping of item values to display labels
            default_order: Optional default ordering
            enable_rename: If True, allow inline renaming
            rename_map: Existing rename mapping to pre-fill inputs

        Returns:
            Reordered list of items, or ``(order, renames)`` when
            *enable_rename* is True.
        """
        st.markdown(f"**{label}**")

        # Initialize in session state if needed
        ss_key: str = f"{key_prefix}_order_{self.plot_id}"
        if ss_key not in st.session_state:
            st.session_state[ss_key] = resolve_item_order(items, default_order=default_order)

        # Sync if items changed (e.g. data update)
        current_items: list[str] = st.session_state[ss_key]
        if set(current_items) != set(items):
            current_items = resolve_item_order(items, current_order=current_items)
            st.session_state[ss_key] = current_items

        renames: dict[str, str] = dict(rename_map) if rename_map else {}

        # Display items with reordering controls
        for i, item in enumerate(current_items):
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                if enable_rename:
                    new_name: str = st.text_input(
                        str(item),
                        value=renames.get(str(item), str(item)),
                        key=f"{key_prefix}_rename_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                    if new_name and new_name != str(item):
                        renames[str(item)] = new_name
                    elif str(item) in renames and new_name == str(item):
                        renames.pop(str(item), None)
                else:
                    display_text: str = str(item)
                    if legend_labels and str(item) in legend_labels:
                        display_text = f"{legend_labels[str(item)]} ({item})"
                    st.text(display_text)
            with c2:
                if i > 0:
                    if st.button("↑", key=f"{key_prefix}_up_{i}_{self.plot_id}"):
                        current_items[i], current_items[i - 1] = (
                            current_items[i - 1],
                            current_items[i],
                        )
                        st.session_state[ss_key] = current_items
                        st.rerun()
            with c3:
                if i < len(current_items) - 1:
                    if st.button("↓", key=f"{key_prefix}_down_{i}_{self.plot_id}"):
                        current_items[i], current_items[i + 1] = (
                            current_items[i + 1],
                            current_items[i],
                        )
                        st.session_state[ss_key] = current_items
                        st.rerun()

        if enable_rename:
            return current_items, renames
        return current_items

    def _render_reference_line_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None,
        config: dict[str, Any],
    ) -> None:
        """
        Render UI controls for a horizontal reference line (normalizer baseline).

        Allows the user to select a categorical column and value that acts as
        the normalizer, and draws a red horizontal reference line at the
        normalizer's Y position (typically 1.0 after normalization).

        Args:
            saved_config: Previously saved configuration.
            data: The data being plotted (needed for column/value selection).
            config: Configuration dictionary to populate.
        """
        st.markdown("#### Reference Line (Normalizer)")
        ref_enabled = st.checkbox(
            "Show normalizer reference line",
            value=saved_config.get("reference_line_enabled", False),
            key=f"ref_line_enabled_{self.plot_id}",
            help=(
                "Draw a horizontal dashed line representing the normalizer "
                "baseline. Useful after normalization to highlight Y=1."
            ),
        )
        config["reference_line_enabled"] = ref_enabled

        if ref_enabled and data is not None:
            categorical_cols = data.select_dtypes(
                include=["object", "string", "category"]
            ).columns.tolist()

            with st.expander("Reference Line Settings", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    saved_col = saved_config.get("reference_line_column", "")
                    col_index = (
                        categorical_cols.index(saved_col) if saved_col in categorical_cols else 0
                    )
                    ref_column: str = (
                        st.selectbox(
                            "Normalizer column",
                            options=categorical_cols,
                            index=col_index if categorical_cols else 0,
                            key=f"ref_line_col_{self.plot_id}",
                            help="Categorical column identifying the normalizer",
                        )
                        or ""
                    )

                with col2:
                    ref_value: str | None = None
                    if ref_column and ref_column in data.columns:
                        unique_vals = sorted(data[ref_column].unique().tolist())
                        saved_val = saved_config.get("reference_line_value", "")
                        val_index = unique_vals.index(saved_val) if saved_val in unique_vals else 0
                        ref_value = st.selectbox(
                            "Normalizer value",
                            options=unique_vals,
                            index=val_index if unique_vals else 0,
                            key=f"ref_line_val_{self.plot_id}",
                            help="Value that identifies the baseline",
                        )

                col3, col4, col5 = st.columns(3)
                with col3:
                    ref_y = st.number_input(
                        "Y position",
                        value=float(saved_config.get("reference_line_y", 1.0)),
                        step=0.1,
                        format="%.2f",
                        key=f"ref_line_y_{self.plot_id}",
                        help="Y-axis value where the line is drawn (1.0 for " "normalized data)",
                    )
                with col4:
                    ref_color = st.color_picker(
                        "Line color",
                        value=saved_config.get("reference_line_color", "#FF0000"),
                        key=f"ref_line_color_{self.plot_id}",
                    )
                with col5:
                    ref_width = st.slider(
                        "Line width",
                        min_value=0.5,
                        max_value=4.0,
                        value=float(saved_config.get("reference_line_width", 1.5)),
                        step=0.5,
                        key=f"ref_line_width_{self.plot_id}",
                    )

                ref_style = st.selectbox(
                    "Line style",
                    options=["dash", "dot", "dashdot", "solid"],
                    index=["dash", "dot", "dashdot", "solid"].index(
                        saved_config.get("reference_line_style", "dash")
                    ),
                    key=f"ref_line_style_{self.plot_id}",
                )

                config["reference_line_column"] = ref_column
                config["reference_line_value"] = ref_value
                config["reference_line_y"] = ref_y
                config["reference_line_color"] = ref_color
                config["reference_line_width"] = ref_width
                config["reference_line_style"] = ref_style
