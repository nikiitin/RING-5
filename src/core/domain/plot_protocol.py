"""
Plot Protocol and Type Definitions.

Defines the core interface (protocol) for plot objects, decoupling the core
layer from web layer implementation details. This allows core services to work
with plots without depending on concrete web implementations.

Maintains publication-quality plot abstraction with support for complex
configurations, transformations, and metadata management.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class PlotProtocol(Protocol):
    """
    Protocol defining the core properties of a Plot object.
    Decouples the Core layer from the Web layer's plotting implementation.
    """

    plot_id: int
    name: str
    plot_type: str
    config: Dict[str, Any]
    pipeline: List[Dict[str, Any]]
    pipeline_counter: int
    legend_mappings_by_column: Dict[str, Dict[str, str]]
    legend_mappings: Dict[str, str]
    processed_data: Optional[pd.DataFrame]

    def to_dict(self) -> Dict[str, Any]: ...
