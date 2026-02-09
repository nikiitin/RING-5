"""
Services API Protocol -- Unified facade interface for the services subsystem.

Defines the contract for a complete services API that combines data operations,
compute transformations, pipeline management, variable management, and portfolio
persistence behind a single hierarchical facade.

Architecture:
    ServicesAPI
    +-- data      -> DataServicesAPI (CSV pool, config persistence)
    +-- compute   -> ComputeServicesAPI (arithmetic, outlier, reduction)
    +-- pipeline  -> PipelineServicesAPI (shaper pipeline CRUD + execution)
    +-- variable  -> VariableServicesAPI (gem5 variable management)
    +-- portfolio -> PortfolioServicesAPI (workspace persistence)

Implementations:
    - DefaultServicesAPI: Default implementation composing individual services
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import pandas as pd

from src.core.models import PlotProtocol

# ---------------------------------------------------------------------------
# Data Services Sub-API
# ---------------------------------------------------------------------------


@runtime_checkable
class DataServicesAPI(Protocol):
    """Protocol for data storage and retrieval operations.

    Covers CSV pool management and saved configuration persistence.
    """

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """List available CSV files in the pool with metadata."""
        ...

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a CSV file to the pool. Returns pool path."""
        ...

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Delete a CSV file from the pool."""
        ...

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file returning a DataFrame."""
        ...

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        ...

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load a configuration from file."""
        ...

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """List all saved configurations."""
        ...

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        ...

    # -- Cache Management --

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return CSV pool cache statistics."""
        ...

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        ...


# ---------------------------------------------------------------------------
# Compute Services Sub-API
# ---------------------------------------------------------------------------


@runtime_checkable
class ComputeServicesAPI(Protocol):
    """Protocol for stateless data transformation operations.

    Groups arithmetic, outlier removal, reduction, and column-merge
    operations used by the data-manager UI components (managers).
    """

    # -- Arithmetic (Preprocessor) --

    def list_operators(self) -> List[str]:
        """Return supported binary arithmetic operators."""
        ...

    def apply_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        ...

    # -- Mixer (Multi-column merge) --

    def apply_mixer(
        self,
        df: pd.DataFrame,
        dest_col: str,
        source_cols: List[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into one with SD propagation."""
        ...

    def validate_merge_inputs(
        self,
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
    ) -> List[str]:
        """Validate inputs for merge/mixer operations."""
        ...

    # -- Outlier Removal --

    def remove_outliers(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> pd.DataFrame:
        """Remove statistical outliers based on Q3 threshold."""
        ...

    def validate_outlier_inputs(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> List[str]:
        """Validate inputs for outlier removal."""
        ...

    # -- Seeds Reduction --

    def reduce_seeds(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> pd.DataFrame:
        """Aggregate data across random seeds (mean + stdev)."""
        ...

    def validate_seeds_reducer_inputs(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> List[str]:
        """Validate inputs for seeds reduction."""
        ...


# ---------------------------------------------------------------------------
# Pipeline Services Sub-API
# ---------------------------------------------------------------------------


@runtime_checkable
class PipelineServicesAPI(Protocol):
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


# ---------------------------------------------------------------------------
# Variable Services Sub-API
# ---------------------------------------------------------------------------


@runtime_checkable
class VariableServicesAPI(Protocol):
    """Protocol for gem5 variable management operations.

    Covers CRUD, search, entry aggregation, and formatting for
    parser variables.
    """

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        ...

    def add_variable(
        self,
        variables: List[Dict[str, Any]],
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Add a new variable to the list."""
        ...

    def update_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update an existing variable at the specified index."""
        ...

    def delete_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
    ) -> List[Dict[str, Any]]:
        """Delete a variable at the specified index."""
        ...

    def ensure_variable_ids(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all variables have unique IDs."""
        ...

    def filter_internal_stats(self, entries: List[str]) -> List[str]:
        """Filter out internal gem5 statistics from entry list."""
        ...

    def find_variable_by_name(
        self,
        variables: List[Dict[str, Any]],
        name: str,
        exact: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Find a variable by name (exact or regex match)."""
        ...

    def aggregate_discovered_entries(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> List[str]:
        """Aggregate entries for a variable across scanned files."""
        ...

    def aggregate_distribution_range(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Aggregate min/max range for a distribution variable."""
        ...

    def parse_comma_separated_entries(self, entries_str: str) -> List[str]:
        """Parse comma-separated entry string into list."""
        ...

    def format_entries_as_string(self, entries: List[str]) -> str:
        """Format list of entries as comma-separated string."""
        ...


# ---------------------------------------------------------------------------
# Portfolio Services Sub-API
# ---------------------------------------------------------------------------


@runtime_checkable
class PortfolioServicesAPI(Protocol):
    """Protocol for workspace persistence operations.

    Manages complete workspace snapshots (portfolios) including data,
    plots, configurations, and parser state.
    """

    def list_portfolios(self) -> List[str]:
        """List all available saved portfolios."""
        ...

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame,
        plots: List[PlotProtocol],
        config: Dict[str, Any],
        plot_counter: int,
        csv_path: Optional[str] = None,
        parse_variables: Optional[List[str]] = None,
    ) -> None:
        """Serialize and save the current workspace state."""
        ...

    def load_portfolio(self, name: str) -> Dict[str, Any]:
        """Load a portfolio by name."""
        ...

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        ...


# ---------------------------------------------------------------------------
# Top-Level Services API
# ---------------------------------------------------------------------------


@runtime_checkable
class ServicesAPI(Protocol):
    """Unified facade for the services subsystem.

    Provides hierarchical access to all service operations through
    specialized sub-APIs. Analogous to ``ParserAPI`` in the parsing module.

    Usage::

        api = DefaultServicesAPI(state_manager)
        pool = api.data.load_csv_pool()
        result = api.compute.remove_outliers(df, col, groups)
        api.pipeline.save_pipeline("my_pipeline", config)
    """

    @property
    def data(self) -> DataServicesAPI:
        """Access data storage and retrieval operations."""
        ...

    @property
    def compute(self) -> ComputeServicesAPI:
        """Access stateless data transformation operations."""
        ...

    @property
    def pipeline(self) -> PipelineServicesAPI:
        """Access pipeline and shaper operations."""
        ...

    @property
    def variable(self) -> VariableServicesAPI:
        """Access gem5 variable management operations."""
        ...

    @property
    def portfolio(self) -> PortfolioServicesAPI:
        """Access workspace persistence operations."""
        ...
