"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
import copy
from typing import Any, Self

import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.common.dataframe_copy import copy_dataframe
from src.core.models.data_models import PipelineStep
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.relayout import update_config_from_relayout
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure
from src.web.pages.ui.plotting.plot_config_ui import PlotConfigUIMixin
from src.web.pages.ui.plotting.styles import StyleApplicator, StyleUIFactory


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
        self.last_generated_fig: go.Figure | MplFigure | None = None
        self.last_traces: TraceBuildResult | None = None
        self.last_figure_spec: FigureConfig | None = None
        self.last_figure_cache_key: str | None = None
        self.pipeline: list[PipelineStep] = []
        self.pipeline_counter: int = 0

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

        prepared = prepare_figure(data, config, self.plot_type, self.create_traces)
        self.config = prepared.config
        result = prepared.trace_result
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
        """Release the owned manager and discard derived render references."""
        # [impl->req~ring5.plots.delete~1]
        self._release_figure_manager(self.last_generated_fig)
        self._clear_render_state()

    @staticmethod
    def _release_figure_manager(figure: go.Figure | MplFigure | None) -> None:
        """Deregister only this figure's manager, preserving borrowed artist content."""
        if isinstance(figure, MplFigure):
            import matplotlib.pyplot as plt

            plt.close(figure)

    def _clear_render_state(self) -> None:
        """Forget references without releasing a figure borrowed by a shallow copy."""
        self.last_generated_fig = None
        self.last_traces = None
        self.last_figure_spec = None
        self.last_figure_cache_key = None

    def copy_without_render_state(self) -> Self:
        """Return a shallow domain view without borrowing the source's artifacts."""
        clone = copy.copy(self)
        clone._clear_render_state()
        return clone

    def publish_figure(
        self,
        figure: go.Figure | MplFigure,
        prepared: PreparedFigure,
        *,
        cache_key: str | None = None,
    ) -> None:
        """Publish one successfully built native artifact and its exact preparation.

        Args:
            figure: Completed figure from the selected native builder.
            prepared: Effective configuration, traces and resolved style used to build it.
            cache_key: Verified reuse identity, or ``None`` when reuse is disabled.
        """
        # [impl->req~ring5.plots.independent-state~1]
        if isinstance(figure, MplFigure):
            figure._ring5_spec = prepared.spec  # type: ignore[attr-defined]
        self._release_figure_manager(figure)
        if self.last_generated_fig is not figure:
            self._release_figure_manager(self.last_generated_fig)
        self.config = prepared.config
        self.last_traces = prepared.trace_result
        self.last_figure_spec = prepared.spec
        self.last_figure_cache_key = cache_key
        self.last_generated_fig = figure

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

        Portfolios retain this snapshot independently from processed plot data.
        """
        self.source_data = copy_dataframe(data) if data is not None else None
        self.invalidate_figure()

    def apply_common_layout(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """Apply common layout settings via StyleApplicator."""
        self._applicator.plot_type = self.plot_type
        return self._applicator.apply_styles(fig, config)

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
            "source_data": TypedTableCodec.encode(self.source_data),
            "processed_data": TypedTableCodec.encode(self.processed_data),
            "pipeline": self.pipeline,
            "pipeline_counter": self.pipeline_counter,
        }
