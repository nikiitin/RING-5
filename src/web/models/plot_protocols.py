"""Typed plot-controller, neutral-source and native-artifact contracts.

Controllers depend on these protocols instead of concrete plot strategies.
The composition layer injects lifecycle, registry and pipeline operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self, runtime_checkable

from collections.abc import Mapping, Sequence
import pandas as pd

from src.core.common.plot_render_state import PlotRenderState
from src.core.models.data_models import PipelineStep
from src.web.models.render_artifact import RenderArtifact

if TYPE_CHECKING:
    from src.core.models.visualization.trace_build_result import TraceBuildResult
    from src.core.state.state_manager import StateManager

# Plot Object Protocols


@runtime_checkable
class PlotHandle(Protocol):
    """
    Contract for a plot object as seen by controllers.

    Exposes only the data attributes controllers need to orchestrate
    lifecycle, pipeline, and rendering. Satisfied by ``BasePlot`` without
    any modification.

    Controllers type their ``plot`` parameter as ``PlotHandle`` instead of
    importing the concrete ``BasePlot`` class.
    """

    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    source_data: pd.DataFrame | None
    processed_data: pd.DataFrame | None
    pipeline: list[PipelineStep]
    pipeline_counter: int

    def replace_processed_data(self, data: pd.DataFrame | None) -> None:
        """Replace processed data and invalidate all derived render state."""
        raise NotImplementedError

    def replace_source_data(self, data: pd.DataFrame | None) -> None:
        """Replace the private source-row snapshot used for drill-down."""
        raise NotImplementedError


class ConfigRenderer(Protocol):
    """
    Contract for plot-type-specific config UI rendering.

    Satisfied by ``BasePlot`` through ``render_config_ui`` and
    ``render_settings_section``.

    Used by render_controller to delegate type-specific widget rendering
    without importing the concrete ``BasePlot`` class.
    """

    plot_id: int

    def render_config_ui(self, data: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
        """Render plot-specific data mapping controls and return their configuration."""
        raise NotImplementedError

    def render_settings_section(
        self,
        section: str | None,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Render one settings section and return its updated configuration."""
        raise NotImplementedError


class PlotRenderSource(PlotHandle, Protocol):
    """Registered neutral trace source and atomic native artifact owner."""

    render_state: PlotRenderState[RenderArtifact]

    @property
    def render_artifact(self) -> RenderArtifact:
        """Capture one complete native/configuration/preparation/key generation."""
        raise NotImplementedError

    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Build neutral traces using the supplied owned data and configuration."""
        raise NotImplementedError

    def copy_without_render_state(self) -> Self:
        """Return a detached domain view without borrowing live native artifacts."""
        raise NotImplementedError

    def publish_render_artifact(self, artifact: RenderArtifact) -> None:
        """Atomically publish one completely built native artifact."""
        raise NotImplementedError


@runtime_checkable
class RenderablePlot(PlotRenderSource, ConfigRenderer, Protocol):
    """Neutral rendering, native ownership and the current configuration UI facets."""

    def invalidate_figure(self) -> None:
        """Discard derived artifacts while retaining the plot's current configuration."""
        raise NotImplementedError

    def update_from_relayout(self, relayout_data: dict[str, Any]) -> bool:
        """Apply a genuine native wire event and report configuration changes."""
        raise NotImplementedError


# Service Protocols


class PlotLifecycleService(Protocol):
    """
    Contract for plot lifecycle operations.

    The page layer wraps ``PlotService`` static methods into an adapter
    that satisfies this protocol.
    """

    def create_plot(self, name: str, plot_type: str, state_manager: StateManager) -> PlotHandle:
        """Create, register, and return a plot."""
        raise NotImplementedError

    def delete_plot(self, plot_id: int, state_manager: StateManager) -> None:
        """Delete a plot by identifier."""
        raise NotImplementedError

    def duplicate_plot(self, plot: PlotHandle, state_manager: StateManager) -> PlotHandle:
        """Copy, register, and return a plot."""
        raise NotImplementedError

    def change_plot_type(
        self, plot: PlotHandle, new_type: str, state_manager: StateManager
    ) -> PlotHandle:
        """Replace a plot with an equivalent instance of another type."""
        raise NotImplementedError


class PlotTypeRegistry(Protocol):
    """
    Contract for querying available plot types.

    The page layer wraps ``PlotFactory.get_available_plot_types()``
    into an adapter that satisfies this protocol.
    """

    def get_available_types(self) -> list[str]:
        """Return registered plot-type identifiers."""
        raise NotImplementedError


class PipelineExecutor(Protocol):
    """
    Contract for pipeline operations (apply shapers, configure shaper UI).

    The page adapter combines the session shapers facade with configuration components.
    """

    def apply_shapers(
        self,
        data: pd.DataFrame,
        configs: Sequence[Mapping[str, object]],
    ) -> pd.DataFrame:
        """Apply a shaper pipeline to data."""
        raise NotImplementedError

    def configure_shaper(
        self,
        shaper_type: str,
        data: pd.DataFrame,
        shaper_id: int,
        config: Mapping[str, object] | None,
        owner_id: int,
    ) -> Mapping[str, object]:
        """Render a shaper editor and return its configuration."""
        raise NotImplementedError
