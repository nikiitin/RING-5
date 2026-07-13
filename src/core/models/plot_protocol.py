"""
Plot Protocol and Type Definitions.

Defines the core interface (protocol) for plot objects, decoupling the core
layer from web layer implementation details. This allows core services to work
with plots without depending on concrete web implementations.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from src.core.models.data_models import PipelineStep


@runtime_checkable
class PlotProtocol(Protocol):
    """
    Protocol defining the core properties of a Plot object.
    Decouples the Core layer from the Web layer's plotting implementation.
    """

    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]
    pipeline: list[PipelineStep]
    pipeline_counter: int
    legend_mappings_by_column: dict[str, dict[str, str]]
    legend_mappings: dict[str, str]
    processed_data: pd.DataFrame | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plot to a dictionary."""
        raise NotImplementedError


# Type alias: a callable that deserializes a dict into a PlotProtocol.
# Injected at startup so the core layer never imports web-layer classes.
PlotDeserializer = Callable[[dict[str, Any]], PlotProtocol | None]
