"""
Default implementation of the DataServicesAPI protocol.

Delegates to CsvPoolService, ConfigService, DatasetSnapshotService,
VariableService, and PortfolioService.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pandas as pd

from src.core.models import (
    AnalysisRecipe,
    AnalysisRecipeInfo,
    DatasetSnapshotInfo,
    PlotProtocol,
    PortfolioData,
    PortfolioBundleContents,
    PortfolioBundleInfo,
    PortfolioDiff,
    PortfolioIntegrityReport,
    PortfolioRevisionInfo,
    RecipeExport,
    RecipeParameter,
    RecipeScalar,
    RecipeSource,
)
from src.core.models.data_models import (
    CacheStatsInfo,
    CsvPoolEntry,
    ParseVariableConfig,
    PipelineConfigConflictPolicy,
    PipelineConfigImportResult,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.portfolio_bundle_service import PortfolioBundleService
from src.core.services.data_services.variable_service import VariableService
from src.core.services.analysis_recipe_automation_service import (
    AnalysisRecipeAutomationService,
)
from src.core.state.state_manager import StateManager


class DefaultDataServicesAPI:
    """Default implementation of DataServicesAPI.

    Delegates to CsvPoolService, ConfigService, DatasetSnapshotService,
    VariableService, and PortfolioService.
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with a StateManager for portfolio serialization."""
        self._portfolio_service = PortfolioService(state_manager)
        self._analysis_recipe_service = AnalysisRecipeService(state_manager)

    # -- CSV Pool --

    def load_csv_pool(self) -> list[CsvPoolEntry]:
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

    # -- Configuration Persistence --

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """Save a configuration to disk. Returns saved file path."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> SavedConfigData:
        """Load a configuration from file."""
        return ConfigService.load_configuration(config_path)

    def export_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> bytes:
        """Serialize a validated configuration as portable versioned JSON."""
        return ConfigService.export_configuration(name, description, shapers_config, csv_path)

    def import_configuration(
        self,
        payload: str | bytes | bytearray,
        *,
        conflict: PipelineConfigConflictPolicy = "error",
    ) -> PipelineConfigImportResult:
        """Validate and save a current or legacy portable configuration."""
        return ConfigService.import_configuration(payload, conflict=conflict)

    def load_saved_configs(self) -> list[SavedConfigEntry]:
        """List all saved configurations."""
        return ConfigService.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return ConfigService.delete_configuration(config_path)

    # -- Cache Management --

    def get_cache_stats(self) -> CacheStatsInfo:
        """Return CSV pool cache statistics."""
        return CsvPoolService.get_cache_stats()

    def clear_caches(self) -> None:
        """Clear all CSV pool caches."""
        CsvPoolService.clear_caches()

    # -- Reusable Dataset Snapshots --

    def list_dataset_snapshots(self) -> tuple[DatasetSnapshotInfo, ...]:
        """List locally saved dataset snapshots without loading payloads."""
        return DatasetSnapshotService.list_snapshots()

    def save_dataset_snapshot(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        source_dataset: str,
        overwrite: bool = False,
    ) -> DatasetSnapshotInfo:
        """Persist an exact fingerprinted dataset snapshot."""
        return DatasetSnapshotService.save_snapshot(
            name,
            data,
            source_dataset=source_dataset,
            overwrite=overwrite,
        )

    def load_dataset_snapshot(self, name: str) -> tuple[DatasetSnapshotInfo, pd.DataFrame]:
        """Load and verify a fingerprinted dataset snapshot."""
        return DatasetSnapshotService.load_snapshot(name)

    def delete_dataset_snapshot(self, name: str) -> None:
        """Delete one locally saved dataset snapshot."""
        DatasetSnapshotService.delete_snapshot(name)

    # -- Variable Management --

    def generate_variable_id(self) -> str:
        """Generate a unique variable identifier."""
        return VariableService.generate_variable_id()

    def add_variable(
        self,
        variables: list[ParseVariableConfig],
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Add a new variable to the list."""
        return VariableService.add_variable(variables, var_config)

    def update_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
        var_config: ParseVariableConfig,
    ) -> list[ParseVariableConfig]:
        """Update an existing variable at the specified index."""
        return VariableService.update_variable(variables, index, var_config)

    def delete_variable(
        self,
        variables: list[ParseVariableConfig],
        index: int,
    ) -> list[ParseVariableConfig]:
        """Delete a variable at the specified index."""
        return VariableService.delete_variable(variables, index)

    def ensure_variable_ids(
        self, variables: list[ParseVariableConfig]
    ) -> list[ParseVariableConfig]:
        """Ensure all variables have unique IDs."""
        return VariableService.ensure_variable_ids(variables)

    def filter_internal_stats(
        self,
        entries: list[str],
        internal_stats: frozenset[str] | None = None,
    ) -> list[str]:
        """Filter out internal simulator statistics from entry list."""
        return VariableService.filter_internal_stats(entries, internal_stats)

    def find_variable_by_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
        exact: bool = True,
    ) -> ParseVariableConfig | None:
        """Find a variable by name (exact or regex match)."""
        return VariableService.find_variable_by_name(variables, name, exact)

    def aggregate_discovered_entries(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Aggregate entries for a variable across scanned files."""
        return VariableService.aggregate_discovered_entries(snapshot, var_name)

    def aggregate_distribution_range(
        self,
        snapshot: list[ScannedVariableDict],
        var_name: str,
    ) -> tuple[float | None, float | None]:
        """Aggregate min/max range for a distribution variable."""
        return VariableService.aggregate_distribution_range(snapshot, var_name)

    def parse_comma_separated_entries(self, entries_str: str) -> list[str]:
        """Parse comma-separated entry string into list."""
        return VariableService.parse_comma_separated_entries(entries_str)

    def format_entries_as_string(self, entries: list[str]) -> str:
        """Format list of entries as comma-separated string."""
        return VariableService.format_entries_as_string(entries)

    def find_entries_for_variable(
        self,
        available_variables: list[ScannedVariableDict],
        var_name: str,
    ) -> list[str]:
        """Find all entries for a variable by searching available/scanned variables."""
        return VariableService.find_entries_for_variable(available_variables, var_name)

    def update_scanned_entries(
        self,
        scanned_vars: list[ScannedVariableDict],
        var_name: str,
        new_entries: list[str],
    ) -> list[ScannedVariableDict]:
        """Update or add entries for a variable in the scanned variables list."""
        return VariableService.update_scanned_entries(scanned_vars, var_name, new_entries)

    def has_variable_with_name(
        self,
        variables: list[ParseVariableConfig],
        name: str,
    ) -> bool:
        """Check if a variable with the given name already exists."""
        return VariableService.has_variable_with_name(variables, name)

    def build_statistics_list(
        self,
        selected: dict[str, bool],
    ) -> list[str]:
        """Build a list of selected statistics from a boolean mapping."""
        return VariableService.build_statistics_list(selected)

    # -- Portfolio Management --

    def list_portfolios(self) -> list[str]:
        """List all available saved portfolios."""
        return self._portfolio_service.list_portfolios()

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame | None,
        plots: list[PlotProtocol],
        config: dict[str, Any],
        plot_counter: int,
        csv_path: str | None = None,
        parse_variables: list[ParseVariableConfig] | None = None,
        figure_spec_enricher: None | (
            Callable[[dict[str, Any], str], dict[str, Any] | None]
        ) = None,
        overwrite: bool = True,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> None:
        """Serialize and save the current workspace state."""
        self._portfolio_service.save_portfolio(
            name,
            data,
            plots,
            config,
            plot_counter,
            csv_path,
            parse_variables,
            figure_spec_enricher,
            overwrite,
            signing_key,
            signing_key_id,
        )

    def load_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioData:
        """Load a portfolio by name."""
        return self._portfolio_service.load_portfolio(
            name,
            signing_key=signing_key,
            require_signature=require_signature,
        )

    def verify_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
    ) -> PortfolioIntegrityReport:
        """Inspect a saved portfolio's checksums and optional signature."""
        return self._portfolio_service.verify_portfolio(name, signing_key=signing_key)

    def export_portfolio_bundle(
        self,
        name: str,
        *,
        snapshot_name: str | None = None,
        results: Mapping[str, bytes] | None = None,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> bytes:
        """Build a portable bundle from a saved portfolio and optional artifacts."""
        snapshot = (
            (snapshot_name, DatasetSnapshotService.export_snapshot(snapshot_name))
            if snapshot_name is not None
            else None
        )
        return PortfolioBundleService.create(
            name,
            self._portfolio_service.export_portfolio_bytes(name),
            dataset_snapshot=snapshot,
            results=results,
            signing_key=signing_key,
            signing_key_id=signing_key_id,
        )

    def inspect_portfolio_bundle(
        self,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleInfo:
        """Validate portable bundle metadata without changing application state."""
        return PortfolioBundleService.inspect(
            payload,
            signing_key=signing_key,
            require_signature=require_signature,
        )

    def read_portfolio_bundle(
        self,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleContents:
        """Read every portable bundle artifact after full verification."""
        return PortfolioBundleService.read(
            payload,
            signing_key=signing_key,
            require_signature=require_signature,
        )

    def list_portfolio_revisions(self, name: str) -> tuple[PortfolioRevisionInfo, ...]:
        """List immutable saved versions for a named portfolio."""
        return self._portfolio_service.list_portfolio_revisions(name)

    def load_portfolio_revision(self, name: str, revision_id: str) -> PortfolioData:
        """Load one immutable saved portfolio version."""
        return self._portfolio_service.load_portfolio_revision(name, revision_id)

    def compare_portfolio_revisions(
        self,
        name: str,
        before_revision: str,
        after_revision: str,
    ) -> PortfolioDiff:
        """Compare tracked fields in two saved portfolio versions."""
        return self._portfolio_service.compare_portfolio_revisions(
            name,
            before_revision,
            after_revision,
        )

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio."""
        self._portfolio_service.delete_portfolio(name)

    # -- Analysis recipes --

    def capture_analysis_recipe(
        self,
        name: str,
        *,
        description: str = "",
        parameters: Sequence[RecipeParameter] = (),
        source: RecipeSource | None = None,
        transformations: Sequence[ShaperStepConfig] = (),
        exports: Sequence[RecipeExport] = (),
    ) -> AnalysisRecipe:
        """Capture current source provenance, plots, and pipelines as a recipe."""
        return self._analysis_recipe_service.capture(
            name,
            description=description,
            parameters=parameters,
            source=source,
            transformations=transformations,
            exports=exports,
        )

    def save_analysis_recipe(self, recipe: AnalysisRecipe, *, overwrite: bool = False) -> str:
        """Persist a validated recipe by logical name."""
        return AnalysisRecipeService.save(recipe, overwrite=overwrite)

    def list_analysis_recipes(self) -> tuple[AnalysisRecipeInfo, ...]:
        """List readable saved analysis recipes."""
        return AnalysisRecipeService.list()

    def load_analysis_recipe(self, name: str) -> AnalysisRecipe:
        """Load a saved analysis recipe by name."""
        return AnalysisRecipeService.load(name)

    def delete_analysis_recipe(self, name: str) -> None:
        """Delete a saved analysis recipe."""
        AnalysisRecipeService.delete(name)

    def export_analysis_recipe(self, recipe: AnalysisRecipe) -> bytes:
        """Serialize a validated recipe as deterministic versioned JSON."""
        return AnalysisRecipeService.dumps(recipe)

    def decode_analysis_recipe(self, payload: str | bytes | bytearray) -> AnalysisRecipe:
        """Decode validated recipe JSON without saving or executing it."""
        return AnalysisRecipeService.loads(payload)

    def export_analysis_recipe_script(self, recipe: AnalysisRecipe) -> bytes:
        """Render a recipe as a documented public-API Python script."""
        return AnalysisRecipeAutomationService.export_script(recipe)

    def export_analysis_recipe_notebook(self, recipe: AnalysisRecipe) -> bytes:
        """Render a recipe as a documented public-API Jupyter notebook."""
        return AnalysisRecipeAutomationService.export_notebook(recipe)

    def import_analysis_recipe(
        self, payload: str | bytes | bytearray, *, overwrite: bool = False
    ) -> AnalysisRecipe:
        """Validate and persist one portable recipe document."""
        return AnalysisRecipeService.import_recipe(payload, overwrite=overwrite)

    def materialize_analysis_recipe(
        self,
        recipe: AnalysisRecipe,
        values: Mapping[str, RecipeScalar] | None = None,
    ) -> AnalysisRecipe:
        """Substitute typed runtime values into a recipe."""
        return AnalysisRecipeService.materialize(recipe, values)
