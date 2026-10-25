"""
Plot Adapters — bridge old concrete classes to protocol contracts.

These adapters wrap the static/class-method services (``PlotService``,
``PlotFactory``), facade shaper operations, and the ``configure_shaper`` editor
into instance-method objects that satisfy the protocol
contracts defined in ``src.web.models.plot_protocols``.

Layer: Pages (Layer 1) — MAY import from ``pages.ui.plotting.*``.

Usage::

    # In manage_plots.py (thin page layer):
    from src.web.pages.plot_adapters import (
        PipelineExecutorAdapter,
        PlotLifecycleAdapter,
        PlotTypeRegistryAdapter,
    )

    lifecycle = PlotLifecycleAdapter()
    registry  = PlotTypeRegistryAdapter()
    pipeline  = PipelineExecutorAdapter(api.shapers)

    creation = PlotCreationController(api, ui_state, lifecycle, registry)
    pipeline_ctrl = PipelineController(api, ui_state, pipeline)
    render = PlotRenderController(api, ui_state, lifecycle, registry)
"""

from typing import TYPE_CHECKING, cast

from collections.abc import Mapping, Sequence
import pandas as pd

from src.web.models.plot_protocols import PlotHandle
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.pages.ui.shaper_config import configure_shaper

if TYPE_CHECKING:
    from src.core.services.shapers.shapers_api import ShapersAPI
    from src.core.state.state_manager import StateManager


class PlotLifecycleAdapter:
    """
    Adapts ``PlotService`` static methods to ``PlotLifecycleService`` protocol.

    Wraps create, delete, duplicate, and change_plot_type operations.
    """

    def create_plot(self, name: str, plot_type: str, state_manager: "StateManager") -> PlotHandle:
        """Create a new plot via PlotService."""
        return PlotService.create_plot(name, plot_type, state_manager)

    def delete_plot(self, plot_id: int, state_manager: "StateManager") -> None:
        """Delete a plot via PlotService."""
        PlotService.delete_plot(plot_id, state_manager)

    def duplicate_plot(self, plot: PlotHandle, state_manager: "StateManager") -> PlotHandle:
        """Duplicate a plot via PlotService."""
        return PlotService.duplicate_plot(cast(BasePlot, plot), state_manager)

    def change_plot_type(
        self, plot: PlotHandle, new_type: str, state_manager: "StateManager"
    ) -> PlotHandle:
        """Change a plot's type via PlotService."""
        return PlotService.change_plot_type(cast(BasePlot, plot), new_type, state_manager)


class PlotTypeRegistryAdapter:
    """
    Adapts ``PlotFactory`` class methods to ``PlotTypeRegistry`` protocol.

    Wraps the plot type registry query.
    """

    def get_available_types(self) -> list[str]:
        """Get available plot type keys."""
        return PlotFactory.get_available_plot_types()


class PipelineExecutorAdapter:
    """
    Executes through the shapers facade and dispatches editor components.
    """

    def __init__(self, shapers: "ShapersAPI") -> None:
        """Use the session facade for execution and current editor metadata."""
        self._shapers = shapers

    def apply_shapers(
        self,
        data: pd.DataFrame,
        configs: Sequence[Mapping[str, object]],
    ) -> pd.DataFrame:
        """Apply a sequence of shaper configs to data."""
        return self._shapers.process_pipeline(data, configs)

    def configure_shaper(
        self,
        shaper_type: str,
        data: pd.DataFrame,
        shaper_id: int,
        config: Mapping[str, object] | None,
        owner_id: int,
    ) -> Mapping[str, object]:
        """Render shaper-specific config widgets and return config dict."""
        return configure_shaper(
            shaper_type,
            data,
            shaper_id,
            config,
            owner_id=owner_id,
            display_names=self._shapers.get_shaper_display_names(),
        )
