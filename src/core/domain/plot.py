from typing import Any, Dict, List, Protocol, runtime_checkable


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

    def to_dict(self) -> Dict[str, Any]: ...
