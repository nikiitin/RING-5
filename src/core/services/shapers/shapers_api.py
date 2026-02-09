"""
Shapers API Protocol -- Interface for shaper pipeline operations.

Defines the contract for pipeline CRUD (save/load/list/delete) and
execution of shaper transformation chains.
"""

from typing import Any, Dict, List, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class ShapersAPI(Protocol):
    """Protocol for pipeline and shaper transformation operations.

    Covers pipeline CRUD (save/load/list/delete) and execution of
    shaper transformation chains.
    """

    def list_pipelines(self) -> List[str]:
        """List all available saved pipelines."""
        ...

    def save_pipeline(
        self,
        name: str,
        pipeline_config: List[Dict[str, Any]],
        description: str = "",
    ) -> None:
        """Save a pipeline configuration to disk."""
        ...

    def load_pipeline(self, name: str) -> Dict[str, Any]:
        """Load a pipeline configuration by name."""
        ...

    def delete_pipeline(self, name: str) -> None:
        """Delete a pipeline configuration."""
        ...

    def process_pipeline(
        self,
        data: pd.DataFrame,
        pipeline_config: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        ...

    def create_shaper(
        self,
        shaper_type: str,
        params: Dict[str, Any],
    ) -> Any:
        """Create a shaper instance from type and parameters."""
        ...

    def get_available_shaper_types(self) -> List[str]:
        """Return all registered shaper type identifiers."""
        ...
