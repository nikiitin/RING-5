"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
import copy
from typing import Any, Self

import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.common.dataframe_copy import copy_dataframe
from src.core.common.plot_render_state import PlotRenderState
from src.core.common.numbered_axis import numbered_axis_modes
from src.core.common.plot_payload import validate_plot_config_keys, validate_plot_config_values
from src.core.models.data_models import PipelineStep
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.models.plot_config import PlotConfig
from src.web.rendering.relayout import update_config_from_relayout
from src.web.models.render_artifact import RenderArtifact
from src.web.pages.ui.plotting.plot_config_ui import PlotConfigUIMixin
from src.web.pages.ui.plotting.styles import StyleUIFactory


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
        self.source_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None
        self.render_state: PlotRenderState[RenderArtifact] = PlotRenderState(RenderArtifact({}))
        self.pipeline: list[PipelineStep] = []
        self.pipeline_counter: int = 0

        # Initialize Style Manager
        self._style_ui = StyleUIFactory.get_strategy(self.plot_id, self.plot_type)

    @property
    def config(self) -> PlotConfig:
        """Return an owned configuration snapshot; assign an edited mapping to publish it."""
        return self.render_artifact.config

    @config.setter
    def config(self, config: PlotConfig) -> None:
        """Own a complete replacement mapping and invalidate its derived generation."""
        validate_plot_config_keys(config, plot_type=self.plot_type)
        validate_plot_config_values(config, plot_type=self.plot_type)
        numbered_axis_modes(config)
        artifact = RenderArtifact(copy.deepcopy(config))
        previous = self.render_state.set_detached_payload(artifact)
        if previous is not None:
            previous.dispose()

    @property
    def render_artifact(self) -> RenderArtifact:
        """Capture the exact current native generation or detached configuration state."""
        artifact = self.render_state.current_payload()
        if artifact is None:
            raise RuntimeError("A plot must retain its current configuration state.")
        return artifact

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

        return changed

    def invalidate_figure(self) -> None:
        """Detach the captured generation while preserving borrowed figure content."""
        # [impl->req~ring5.plots.delete~1]
        retired = self.render_state.detach(self.render_state.snapshot())
        if retired is not None:
            retired.dispose()

    @staticmethod
    def _release_figure_manager(figure: go.Figure | MplFigure | None) -> None:
        """Deregister only this figure's manager, preserving borrowed artist content."""
        if isinstance(figure, MplFigure):
            import matplotlib.pyplot as plt

            plt.close(figure)

    def _clear_render_state(self) -> None:
        """Forget references without releasing a figure borrowed by a shallow copy."""
        self.render_state = PlotRenderState(self.render_artifact.detached())

    def copy_without_render_state(self) -> Self:
        """Return a shallow domain view without borrowing the source's artifacts."""
        clone = copy.copy(self)
        clone._clear_render_state()
        return clone

    def publish_render_artifact(self, artifact: RenderArtifact) -> None:
        """Publish native/configuration/preparation/key state in one atomic generation.

        Args:
            artifact: Complete successfully rendered native figure and its exact inputs.

        Raises:
            ValueError: The artifact has no native figure, engine or preparation.
        """
        # [impl->req~ring5.plots.independent-state~1]
        if artifact.figure is None or artifact.preparation is None or artifact.engine is None:
            raise ValueError("Only a complete native render artifact can be published.")
        # Relinquish this generation's manager now. Later borrowers may register
        # their own manager on the same figure; retirement must never claim it.
        self._release_figure_manager(artifact.figure)
        previous = self.render_state.publish(
            artifact,
            lambda: None,
            detached_payload=artifact.detached(),
        )
        if previous is not None:
            previous.dispose()

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
