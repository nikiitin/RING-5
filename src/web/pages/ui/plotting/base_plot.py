"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.models.data_models import PipelineStep
from src.core.models.plot_config import ShapeConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.services.visualization.plot_interaction import (
    update_config_from_relayout,
)
from src.web.components.plotting.settings import (
    AdvancedSettingsComponent,
    AxesSettingsComponent,
    ColorsSettingsComponent,
    DataLabelsSettingsComponent,
    LayoutSettingsComponent,
    LegendSettingsComponent,
    TypographySettingsComponent,
)
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.styles import StyleManager


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

    def render_display_options(self, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render sizing and layout options via LayoutSettingsComponent."""
        component = LayoutSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config)

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

    def _supports_secondary_legend(self) -> bool:
        """Whether this plot type supports a secondary legend pill.

        Override in subclasses that offer secondary legend features
        independently of dual-axis mode (e.g. numbered X-axis legend).
        """
        return False

    def _supports_tertiary_legend(self) -> bool:
        """Whether this plot type supports a tertiary legend pill.

        Override in subclasses that offer a third level of legend
        (e.g. numbered X-axis annotations when dual-axis is also active).
        Only show tertiary when the plot actually has three legend levels.
        """
        return False

    def _section_layout(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        component = LayoutSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config)

    def _section_typography(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        component = TypographySettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config, key_prefix="theme_")

    def _section_legends(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        has_dual_axis: bool = self.plot_type == "dual_axis_bar_dot" or bool(
            saved_config.get("dual_axis")
        )
        has_secondary: bool = has_dual_axis or self._supports_secondary_legend()
        has_tertiary: bool = self._supports_tertiary_legend() and bool(
            saved_config.get("show_group_labels") or saved_config.get("numbered_xaxis")
        )

        component = LegendSettingsComponent(self.plot_id, self.plot_type)
        return component.render(
            saved_config,
            has_secondary=has_secondary,
            has_tertiary=has_tertiary,
        )

    def _section_axes(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        has_dual_axis: bool = self.plot_type == "dual_axis_bar_dot" or bool(
            saved_config.get("dual_axis")
        )

        component = AxesSettingsComponent(self.plot_id, self.plot_type)
        return component.render(
            saved_config,
            data=data,
            has_dual_axis=has_dual_axis,
            render_specific_fn=self.render_specific_advanced_options,
            render_ordering_fn=self._render_ordering_ui,
        )

    def _render_x_axis_settings(self, saved_config: dict[str, Any], config: dict[str, Any]) -> None:
        """Render X-axis specific settings (tick angle, grid)."""
        st.markdown("#### X-Axis Settings")
        config["show_x_grid"] = st.checkbox(
            "Show Grid",
            value=saved_config.get("show_x_grid", True),
            key=f"show_x_grid_{self.plot_id}",
        )
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

        grid_key = f"{prefix}show_y_grid" if prefix else "show_y_grid"
        config[grid_key] = st.checkbox(
            "Show Grid",
            value=saved_config.get(grid_key, True if not prefix else False),
            key=f"{prefix}show_y_grid_{self.plot_id}",
        )

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
        component = DataLabelsSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config, key_prefix="theme_")

    def _section_colors(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        """Unified palette selector using core PALETTE_REGISTRY."""
        component = ColorsSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config, data=data)

    def _section_advanced(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None
    ) -> dict[str, Any]:
        component = AdvancedSettingsComponent(self.plot_id, self.plot_type)
        return component.render(
            saved_config,
            data=data,
            render_reference_line_fn=self._render_reference_line_ui,
            render_shapes_fn=self._render_shapes_ui,
            render_engine_fn=self._render_engine_specific_controls,
        )

    def _render_engine_specific_controls(
        self,
        saved_config: dict[str, Any],
        config: dict[str, Any],
    ) -> None:
        """Render engine-specific controls. Delegates to engine_settings component."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        render_engine_controls(self.plot_id, saved_config, config)

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

        # 3. Ordering Control (includes inline X-axis & legend rename)
        if data is not None:
            self._render_ordering_ui(saved_config, data, config)

        # 4. Legend & Interactivity
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help="Allows you to drag the legend/title and click to edit text directly on the plot.",
        )

        # Preserve existing series styles (renaming now inline in ordering)
        if "series_styles" not in config:
            config["series_styles"] = saved_config.get("series_styles", {})

        # 5. Reference Line
        self._render_reference_line_ui(saved_config, data, config)

        # 6. Annotations
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
                        help=(
                            "Adds a white border around each bar segment"
                            " to separate stacked items."
                        ),
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
        """Render ordering UI. Delegates to ordering_settings component."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        render_ordering_ui(self.plot_id, saved_config, data, config)

    def _render_shapes_ui(self, saved_config: dict[str, Any]) -> list[ShapeConfig]:
        """Render shapes UI. Delegates to shapes_settings component."""
        from src.web.components.plotting.settings.shapes_settings import (
            render_shapes_ui,
        )

        return render_shapes_ui(self.plot_id, saved_config)

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

        Delegates to the standalone ``render_reorderable_list`` component.
        Kept as a thin wrapper for backward compatibility with subclasses.
        """
        from src.web.components.common.reorderable_list import (
            render_reorderable_list,
        )

        return render_reorderable_list(
            label=label,
            items=items,
            key_prefix=key_prefix,
            plot_id=self.plot_id,
            legend_labels=legend_labels,
            default_order=default_order,
            enable_rename=enable_rename,
            rename_map=rename_map,
        )

    def _render_reference_line_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None,
        config: dict[str, Any],
    ) -> None:
        """Render reference line UI. Delegates to reference_line_settings component."""
        from src.web.components.plotting.settings.reference_line_settings import (
            render_reference_line_ui,
        )

        render_reference_line_ui(self.plot_id, saved_config, data, config)
