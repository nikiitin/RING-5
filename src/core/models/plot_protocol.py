"""
Plot Protocol and Type Definitions.

Defines the core interface (protocol) for plot objects, decoupling the core
layer from web layer implementation details. This allows core services to work
with plots without depending on concrete web implementations.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from src.core.common.plot_render_state import PlotRenderState
from src.core.models.data_models import PipelineStep


@runtime_checkable
class PlotProtocol(Protocol):
    """
    Protocol defining the core properties of a Plot object.
    Decouples the Core layer from the Web layer's plotting implementation.
    ``render_state`` owns exact payload/retirement pairs. Repository removal detaches
    those bindings without invoking an overridable plot lifecycle method.
    """

    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    pipeline: list[PipelineStep]
    pipeline_counter: int
    source_data: pd.DataFrame | None
    processed_data: pd.DataFrame | None
    render_state: PlotRenderState[Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plot to a dictionary."""
        raise NotImplementedError

    def invalidate_figure(self) -> None:
        """Discard owned derived artifacts after data/configuration changes or removal."""
        raise NotImplementedError

    def replace_pipeline_data(self, source: pd.DataFrame, processed: pd.DataFrame) -> None:
        """Publish an owned, verified original-source/finalized-output pair atomically."""
        raise NotImplementedError

    def replace_processed_data(self, data: pd.DataFrame | None) -> None:
        """Replace processed data and discard derived figure artifacts."""
        raise NotImplementedError


# Type alias: a callable that deserializes a dict into a PlotProtocol.
# Injected at startup so the core layer never imports web-layer classes.
PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
