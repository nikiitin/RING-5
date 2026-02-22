"""
Plot Protocols — contracts between controllers and concrete implementations.

Controllers depend on these protocols instead of importing concrete classes
from ``pages.ui.plotting.*``. The page layer provides concrete implementations
via dependency injection (adapters wrapping old static/class-method services).

Layer: Models (Layer 5) — NO Streamlit dependency.

Protocol Hierarchy::

    PlotHandle            — data attributes every controller needs
    ConfigRenderer        — config-UI rendering facet (BasePlot satisfies this)
    PlotLifecycleService  — create / delete / duplicate / change-type
    PlotTypeRegistry      — list available plot types
    PipelineExecutor      — apply / configure shapers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import pandas as pd

from src.core.models.data_models import PipelineStep, ShaperStepConfig

if TYPE_CHECKING:
    import plotly.graph_objects as go

    from src.core.models.visualization.trace_build_result import TraceBuildResult
    from src.core.state.repository_state_manager import RepositoryStateManager

# ─── Plot Object Protocols ──────────────────────────────────────────────────


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
    processed_data: pd.DataFrame | None
    pipeline: list[PipelineStep]
    pipeline_counter: int


class ConfigRenderer(Protocol):
    """
    Contract for plot-type-specific config UI rendering.

    Satisfied by ``BasePlot`` (which has ``render_config_ui``,
    ``render_advanced_options``, ``render_display_options``,
    ``render_theme_options``, ``render_settings_section``).

    Used by ``ConfigPresenter`` to delegate type-specific widget rendering
    without importing the concrete ``BasePlot`` class.
    """

    plot_id: int

    def render_config_ui(self, data: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]: ...

    def render_advanced_options(
        self, config: dict[str, Any], data: pd.DataFrame
    ) -> dict[str, Any]: ...

    def render_display_options(self, config: dict[str, Any]) -> dict[str, Any]: ...

    def render_theme_options(self, config: dict[str, Any]) -> dict[str, Any]: ...

    def render_settings_section(
        self,
        section: str | None,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class RenderablePlot(PlotHandle, ConfigRenderer, Protocol):
    """
    Combined protocol for plots that support both data access and config rendering.

    Used by ``PlotRenderController`` which needs to read plot data attributes
    (``PlotHandle``) AND render config widgets (``ConfigRenderer``).

    Satisfied by ``BasePlot`` which implements both interfaces.
    Replaces the unsafe ``cast(ConfigRenderer, plot)`` pattern.
    """

    last_generated_fig: go.Figure | None
    last_traces: TraceBuildResult | None

    def create_figure(self, data: pd.DataFrame, config: dict[str, Any]) -> go.Figure: ...

    def apply_common_layout(self, fig: go.Figure, config: dict[str, Any]) -> go.Figure: ...

    def update_from_relayout(self, relayout_data: dict[str, Any]) -> bool: ...


# ─── Service Protocols ──────────────────────────────────────────────────────


class PlotLifecycleService(Protocol):
    """
    Contract for plot lifecycle operations.

    The page layer wraps ``PlotService`` static methods into an adapter
    that satisfies this protocol.
    """

    def create_plot(
        self, name: str, plot_type: str, state_manager: RepositoryStateManager
    ) -> PlotHandle: ...

    def delete_plot(self, plot_id: int, state_manager: RepositoryStateManager) -> None: ...

    def duplicate_plot(
        self, plot: PlotHandle, state_manager: RepositoryStateManager
    ) -> PlotHandle: ...

    def change_plot_type(
        self, plot: PlotHandle, new_type: str, state_manager: RepositoryStateManager
    ) -> PlotHandle: ...


class PlotTypeRegistry(Protocol):
    """
    Contract for querying available plot types.

    The page layer wraps ``PlotFactory.get_available_plot_types()``
    into an adapter that satisfies this protocol.
    """

    def get_available_types(self) -> list[str]: ...


class PipelineExecutor(Protocol):
    """
    Contract for pipeline operations (apply shapers, configure shaper UI).

    The page layer wraps ``apply_shapers()`` and ``configure_shaper()``
    functions into an adapter that satisfies this protocol.
    """

    def apply_shapers(
        self,
        data: pd.DataFrame,
        configs: list[ShaperStepConfig],
    ) -> pd.DataFrame: ...

    def configure_shaper(
        self,
        shaper_type: str,
        data: pd.DataFrame,
        shaper_id: int,
        config: ShaperStepConfig | None,
        owner_id: int | None = None,
    ) -> ShaperStepConfig: ...
