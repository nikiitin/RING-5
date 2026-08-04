"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from src.core.models.data_models import PipelineStep
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.web.models.plot_models import PlotConfig
from src.web.rendering.relayout import update_config_from_relayout
from src.web.pages.ui.plotting.plot_config_ui import PlotConfigUIMixin
from src.web.pages.ui.plotting.styles import StyleApplicator, StyleUIFactory


def _relabel_traces(
    result: TraceBuildResult, legend_labels: dict[str, str] | None
) -> TraceBuildResult:
    """Apply custom legend labels to the engine-agnostic trace names.

    Renaming ``TraceConfig.name`` here — before any connector runs — is the
    single source of truth for legend relabeling, so BOTH the Plotly and
    Matplotlib engines honor it (each reads ``trace.name`` for the legend entry).
    """
    # [impl->req~ring5.figure.ordering-renaming~2]
    if not legend_labels:
        return result
    new_traces = [replace(t, name=legend_labels.get(t.name, t.name)) for t in result.traces]
    return replace(result, traces=new_traces)


class BasePlot(PlotConfigUIMixin, ABC):
    """Abstract base class for all plot types."""

    def __init__(self, plot_id: int, name: str, plot_type: str) -> None:
        """
        Initialize base plot.

        Args:
            plot_id: Unique identifier for the plot
            name: Display name for the plot
            plot_type: Type of plot (bar, line, etc.)
        """
        # [impl->req~ring5.plots.independent-state~1]
        # [impl->req~ring5.shaping.independent-pipelines~1]
        self.plot_id: int = plot_id
        self.name: str = name
        self.plot_type: str = plot_type
        self.config: PlotConfig = {}
        self.source_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None
        self.last_generated_fig: go.Figure | None = None
        self.last_traces: TraceBuildResult | None = None
        self.last_figure_cache_key: str | None = None
        self.pipeline: list[PipelineStep] = []
        self.pipeline_counter: int = 0
        self.legend_mappings_by_column: dict[str, dict[str, str]] = {}
        self.legend_mappings: dict[str, str] = {}

        # Initialize Style Manager
        self._style_ui = StyleUIFactory.get_strategy(self.plot_id, self.plot_type)
        self._applicator = StyleApplicator(self.plot_type)

    @abstractmethod
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
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

    def create_figure(self, data: pd.DataFrame, config: PlotConfig) -> go.Figure:
        # [impl->req~ring5.render.engine-independent-traces~1]
        # [impl->req~ring5.data.semantic-units~1]
        # [impl->req~ring5.figure.accessible-themes~1]
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

        effective_config = SemanticMetadataService.enrich_figure_config(data, config)
        effective_config = AccessibilityService.apply_defaults(effective_config, self.plot_type)
        if effective_config is not config:
            self.config = effective_config
            config = self.config
        result = self.create_traces(data, config)
        result = AccessibilityService.apply_non_color_encodings(result, config)
        # Apply legend relabeling once, engine-agnostically, so both Plotly and
        # Matplotlib (which renders from ``last_traces``) show the custom names.
        result = _relabel_traces(result, config.get("legend_labels"))
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

        Delegates Plotly-event decoding to the web rendering layer
        (``src.web.rendering.relayout.update_config_from_relayout``).

        Args:
            relayout_data: Dictionary of relayout events from Plotly

        Returns:
            True if config changed, False otherwise
        """
        # [impl->req~ring5.figure.interactive-editing~1]
        updated_config, changed = update_config_from_relayout(self.config, relayout_data)

        if changed:
            self.config = updated_config
            self.invalidate_figure()

        return changed

    def invalidate_figure(self) -> None:
        """Discard render artifacts derived from the current data and config."""
        self.last_generated_fig = None
        self.last_traces = None
        self.last_figure_cache_key = None

    def replace_processed_data(self, data: pd.DataFrame | None) -> None:
        """Replace processed data and atomically invalidate render artifacts.

        Args:
            data: New transformed data, or ``None`` when no pipeline result is
                available.
        """
        self.processed_data = data
        self.invalidate_figure()

    def replace_source_data(self, data: pd.DataFrame | None) -> None:
        # [impl->req~ring5.plots.drill-down~1]
        """Store a private source snapshot for reversible row exploration.

        The snapshot is deliberately excluded from portfolio serialization;
        restored legacy plots fall back to their saved processed data.
        """
        self.source_data = data.copy(deep=True) if data is not None else None

    @abstractmethod
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """
        Get the column name used for legend/color coding.

        Args:
            config: Configuration dictionary

        Returns:
            Column name or None
        """

    def apply_common_layout(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """Apply common layout settings via StyleApplicator."""
        return self._applicator.apply_styles(fig, config)

    def generate_figure(self) -> go.Figure:
        """
        Generate and cache the final Plotly figure.

        Calls create_figure (which relabels legend names engine-agnostically)
        then apply_common_layout.
        """
        if self.processed_data is None:
            raise ValueError(f"Plot '{self.name}' has no processed data.")

        fig = self.create_figure(self.processed_data, self.config)
        fig = self.apply_common_layout(fig, self.config)
        self.last_generated_fig = fig
        self.last_figure_cache_key = None
        return fig

    def to_dict(self) -> dict[str, Any]:
        # [impl->req~ring5.portfolio.save~1]
        # [impl->req~ring5.data.semantic-units~1]
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
            "processed_semantics": (
                SemanticMetadataService.to_payload(
                    SemanticMetadataService.inspect(self.processed_data)
                )
                if isinstance(self.processed_data, pd.DataFrame)
                else {}
            ),
            "pipeline": self.pipeline,
            "pipeline_counter": self.pipeline_counter,
            "legend_mappings_by_column": self.legend_mappings_by_column,
            "legend_mappings": self.legend_mappings,
        }
