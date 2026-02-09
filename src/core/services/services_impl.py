"""
Default implementation of the ServicesAPI protocol.

Composes individual service classes into a hierarchical facade,
providing a unified entry point for all service operations.

Each sub-API delegates to the corresponding stateless service class,
keeping this module as a thin orchestration layer.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.core.models import PlotProtocol
from src.core.services.arithmetic_service import ArithmeticService
from src.core.services.config_service import ConfigService
from src.core.services.csv_pool_service import CsvPoolService
from src.core.services.outlier_service import OutlierService
from src.core.services.pipeline_service import PipelineService
from src.core.services.portfolio_service import PortfolioService
from src.core.services.reduction_service import ReductionService
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.shaper import Shaper
from src.core.services.variable_service import VariableService
from src.core.state.state_manager import StateManager

# ---------------------------------------------------------------------------
# Sub-API Implementations
# ---------------------------------------------------------------------------


class DefaultDataServices:
    """Default implementation of DataServicesAPI.

    Delegates to CsvPoolService and ConfigService.
    """

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """List available CSV files in the pool with metadata."""
        return CsvPoolService.load_pool()

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a CSV file to the pool. Returns pool path."""
        return CsvPoolService.add_to_pool(file_path)

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Delete a CSV file from the pool."""
        return CsvPoolService.delete_from_pool(file_path)

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file returning a DataFrame."""
        return CsvPoolService.load_csv_file(file_path)

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict[str, Any]],
        csv_path: Optional[str] = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load a configuration from file."""
        return ConfigService.load_configuration(config_path)

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """List all saved configurations."""
        return ConfigService.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return ConfigService.delete_configuration(config_path)

    # -- Cache Management --

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return CSV pool cache statistics."""
        return CsvPoolService.get_cache_stats()

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        CsvPoolService.clear_caches()


class DefaultComputeServices:
    """Default implementation of ComputeServicesAPI.

    Delegates to ArithmeticService, OutlierService, and ReductionService.
    """

    # -- Arithmetic (Preprocessor) --

    def list_operators(self) -> List[str]:
        """Return supported binary arithmetic operators."""
        return ArithmeticService.list_operators()

    def apply_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        return ArithmeticService.apply_operation(df, operation, src1, src2, dest)

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
        return ArithmeticService.apply_mixer(df, dest_col, source_cols, operation, separator)

    def validate_merge_inputs(
        self,
        df: pd.DataFrame,
        columns: List[str],
        operation: str,
        new_column_name: str,
    ) -> List[str]:
        """Validate inputs for merge/mixer operations."""
        return ArithmeticService.validate_merge_inputs(df, columns, operation, new_column_name)

    # -- Outlier Removal --

    def remove_outliers(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> pd.DataFrame:
        """Remove statistical outliers based on Q3 threshold."""
        return OutlierService.remove_outliers(df, outlier_col, group_by_cols)

    def validate_outlier_inputs(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: List[str],
    ) -> List[str]:
        """Validate inputs for outlier removal."""
        return OutlierService.validate_outlier_inputs(df, outlier_col, group_by_cols)

    # -- Seeds Reduction --

    def reduce_seeds(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> pd.DataFrame:
        """Aggregate data across random seeds (mean + stdev)."""
        return ReductionService.reduce_seeds(df, categorical_cols, statistic_cols)

    def validate_seeds_reducer_inputs(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        statistic_cols: List[str],
    ) -> List[str]:
        """Validate inputs for seeds reduction."""
        return ReductionService.validate_seeds_reducer_inputs(df, categorical_cols, statistic_cols)


class DefaultPipelineServices:
    """Default implementation of PipelineServicesAPI.

    Delegates to PipelineService and ShaperFactory.
    """

    def list_pipelines(self) -> List[str]:
        """List all available saved pipelines."""
        return PipelineService.list_pipelines()

    def save_pipeline(
        self,
        name: str,
        pipeline_config: List[Dict[str, Any]],
        description: str = "",
    ) -> None:
        """Save a pipeline configuration to disk."""
        PipelineService.save_pipeline(name, pipeline_config, description)

    def load_pipeline(self, name: str) -> Dict[str, Any]:
        """Load a pipeline configuration by name."""
        return PipelineService.load_pipeline(name)

    def delete_pipeline(self, name: str) -> None:
        """Delete a pipeline configuration."""
        PipelineService.delete_pipeline(name)

    def process_pipeline(
        self,
        data: pd.DataFrame,
        pipeline_config: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        return PipelineService.process_pipeline(data, pipeline_config)

    def create_shaper(
        self,
        shaper_type: str,
        params: Dict[str, Any],
    ) -> Shaper:
        """Create a shaper instance from type and parameters."""
        return ShaperFactory.create_shaper(shaper_type, params)

    def get_available_shaper_types(self) -> List[str]:
        """Return all registered shaper type identifiers."""
        return ShaperFactory.get_available_types()


class DefaultVariableServices:
    """Default implementation of VariableServicesAPI.

    Delegates to VariableService.
    """

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        return VariableService.generate_variable_id()

    def add_variable(
        self,
        variables: List[Dict[str, Any]],
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Add a new variable to the list."""
        return VariableService.add_variable(variables, var_config)

    def update_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
        var_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update an existing variable at the specified index."""
        return VariableService.update_variable(variables, index, var_config)

    def delete_variable(
        self,
        variables: List[Dict[str, Any]],
        index: int,
    ) -> List[Dict[str, Any]]:
        """Delete a variable at the specified index."""
        return VariableService.delete_variable(variables, index)

    def ensure_variable_ids(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all variables have unique IDs."""
        return VariableService.ensure_variable_ids(variables)

    def filter_internal_stats(self, entries: List[str]) -> List[str]:
        """Filter out internal gem5 statistics from entry list."""
        return VariableService.filter_internal_stats(entries)

    def find_variable_by_name(
        self,
        variables: List[Dict[str, Any]],
        name: str,
        exact: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Find a variable by name (exact or regex match)."""
        return VariableService.find_variable_by_name(variables, name, exact)

    def aggregate_discovered_entries(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> List[str]:
        """Aggregate entries for a variable across scanned files."""
        return VariableService.aggregate_discovered_entries(snapshot, var_name)

    def aggregate_distribution_range(
        self,
        snapshot: List[Dict[str, Any]],
        var_name: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Aggregate min/max range for a distribution variable."""
        return VariableService.aggregate_distribution_range(snapshot, var_name)

    def parse_comma_separated_entries(self, entries_str: str) -> List[str]:
        """Parse comma-separated entry string into list."""
        return VariableService.parse_comma_separated_entries(entries_str)

    def format_entries_as_string(self, entries: List[str]) -> str:
        """Format list of entries as comma-separated string."""
        return VariableService.format_entries_as_string(entries)


class DefaultPortfolioServices:
    """Default implementation of PortfolioServicesAPI.

    Delegates to PortfolioService (the only stateful service).
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with a StateManager for portfolio serialization."""
        self._portfolio_service = PortfolioService(state_manager)

    def list_portfolios(self) -> List[str]:
        """List all available saved portfolios."""
        return self._portfolio_service.list_portfolios()

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
        self._portfolio_service.save_portfolio(
            name, data, plots, config, plot_counter, csv_path, parse_variables
        )

    def load_portfolio(self, name: str) -> Dict[str, Any]:
        """Load a portfolio by name."""
        return self._portfolio_service.load_portfolio(name)

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        self._portfolio_service.delete_portfolio(name)


# ---------------------------------------------------------------------------
# Top-Level Implementation
# ---------------------------------------------------------------------------


class DefaultServicesAPI:
    """Default implementation of ServicesAPI.

    Composes all sub-API implementations and provides the unified
    entry point for service operations.

    Usage::

        api = DefaultServicesAPI(state_manager)
        pool = api.data.load_csv_pool()
        result = api.compute.remove_outliers(df, col, groups)
        api.pipeline.save_pipeline("my_pipeline", config)
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize the services API with all sub-APIs.

        Args:
            state_manager: State manager instance for portfolio operations.
        """
        self._data = DefaultDataServices()
        self._compute = DefaultComputeServices()
        self._pipeline = DefaultPipelineServices()
        self._variable = DefaultVariableServices()
        self._portfolio = DefaultPortfolioServices(state_manager)

    @property
    def data(self) -> DefaultDataServices:
        """Access data storage and retrieval operations."""
        return self._data

    @property
    def compute(self) -> DefaultComputeServices:
        """Access stateless data transformation operations."""
        return self._compute

    @property
    def pipeline(self) -> DefaultPipelineServices:
        """Access pipeline and shaper operations."""
        return self._pipeline

    @property
    def variable(self) -> DefaultVariableServices:
        """Access gem5 variable management operations."""
        return self._variable

    @property
    def portfolio(self) -> DefaultPortfolioServices:
        """Access workspace persistence operations."""
        return self._portfolio
