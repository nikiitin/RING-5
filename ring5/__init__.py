"""RING-5 public Python API — the full workflow, headless.

Everything the web app does, as plain Python::

    import ring5

    with ring5.Session() as s:
        result = s.parse("/path/to/sims", variables=["simTicks"])
        data = s.load(result.csv_path)
        data = s.reduce_seeds(data, ["config_description_abbrev"], ["simTicks"])
        plot = s.create_plot(
            "bar",
            data=data,
            config={"x": "config_description_abbrev", "y": "simTicks"},
        )
        fig = s.render(plot, engine="matplotlib")
        s.export(fig, "out/simticks.pdf", deterministic=True)
        s.save_portfolio("my_paper")

    # Reproduce every figure from a snapshot — the reproducibility flagship:
    ring5.render_portfolio("my_paper", "figs/", engine="matplotlib", fmt="pdf")

Check external dependencies with ``print(ring5.doctor())`` (perl for
parsing; a Chrome-family browser for plotly image export; xelatex for PGF).
Call ``ring5.shutdown()`` once per process to tear down the worker pools
(they restart transparently on next use).

This package is the headless composition root: like ``app.py`` it wires
``src.core`` and the rendering layer together, so the layer rule
("core never imports web") stays intact underneath it.

Import cost: the heavy workflow names (``Session``, ``render_figure``, the
exporters, ``render_portfolio``, …) are loaded lazily on first access
(PEP 562) — ``import ring5`` and the light surface (``doctor``, the error
types, ``shutdown``) stay fast for CLI startup.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from ring5._doctor import DependencyStatus, DoctorReport, doctor
from ring5.errors import (
    ColumnNotFoundError,
    DataLoadError,
    DataValidationError,
    DependencyMissingError,
    ExportError,
    JobError,
    MissingStatError,
    ParseError,
    PipelineError,
    PortfolioError,
    PortfolioVersionError,
    RecipeError,
    RenderError,
    Ring5Error,
    ScanError,
)

# Immutable figure values have no pandas or rendering dependency, so load eagerly.
from ring5.figure_spec import (
    DualAxisOpts,
    FigureSpec,
    LegendOpts,
    ReferenceLineOpts,
)

if TYPE_CHECKING:
    # Static names for mypy/IDEs; at runtime these resolve via __getattr__.
    from src.core.models.accessibility_models import AccessibilityFinding, AccessibilityReport
    from src.core.models.report_models import (
        AnalysisReport,
        ReportFigure,
        ReportNarrative,
        ReportProvenance,
        ReportTable,
    )
    from src.core.models.recipe_models import (
        AnalysisRecipe,
        AnalysisRecipeInfo,
        AnalysisRecipeRunResult,
        RecipeExport,
        RecipeParameter,
        RecipePlot,
        RecipeSource,
    )
    from src.core.models.recipe_matrix_models import (
        AnalysisRecipeMatrixCase,
        AnalysisRecipeMatrixResult,
    )
    from src.core.models.background_job_models import BackgroundJobInfo, BackgroundJobLogEntry
    from src.core.models.schema_contract_models import (
        ColumnContract,
        DatasetSchemaContract,
        SchemaValidationReport,
        SchemaViolation,
    )
    from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics
    from src.core.models.dataset_workspace_models import (
        DatasetInfo,
        DatasetLineage,
        DatasetRevision,
        DatasetSnapshotInfo,
        JoinCardinality,
        JoinDiagnostics,
    )
    from src.core.models.visualization.dashboard_spec import DashboardSpec
    from src.core.models.environment_models import (
        EnvironmentComparison,
        EnvironmentDifference,
        EnvironmentMetadata,
    )
    from src.core.models.figure_theme_models import FigureTheme
    from src.core.models.import_models import (
        ImportColumn,
        ImportColumnCorrection,
        ImportOptions,
        ImportPreview,
        ImportRejectedRow,
    )
    from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
    from src.core.models.visualization.plot_configuration_comparison import (
        ConfigurationDifference,
        PlotConfigurationComparison,
    )
    from src.core.models.visualization.plot_transfer_result import PlotTransferResult
    from src.core.models.portfolio_revision_models import (
        PortfolioDiff,
        PortfolioDiffEntry,
        PortfolioRevisionInfo,
    )
    from src.core.models.portfolio_bundle_models import (
        PortfolioBundleArtifact,
        PortfolioBundleContents,
        PortfolioBundleInfo,
        PortfolioBundleResult,
    )
    from src.core.models.portfolio_integrity_models import (
        PortfolioIntegrityReport,
        PortfolioIntegritySection,
    )
    from src.core.models.parsing_models import (
        ParserPlaygroundResult,
        ScanResult,
        ScannedVariable,
        SourceInstance,
    )
    from src.core.models.data_models import PipelineConfigImportResult
    from src.core.models.visualization.small_multiples_spec import SmallMultiplesSpec
    from src.core.models.portfolio_models import RestoreReport
    from src.core.models.scheduled_report_models import ScheduledReportResult
    from src.core.models.shaper_models import ShaperStepConfig
    from src.core.models.workspace_search_models import (
        WorkspaceSearchResponse,
        WorkspaceSearchResult,
    )
    from src.core.models.workspace_command_models import (
        WorkspaceCommand,
        WorkspaceCommandSearchResponse,
    )
    from src.core.models.workspace_metadata_models import (
        WorkspaceArtifact,
        WorkspaceArtifactResponse,
    )
    from src.core.models.analysis_review_models import (
        AnalysisReviewEvent,
        AnalysisReviewResponse,
        AnalysisReviewTarget,
        AnalysisReviewTargetResponse,
        AnalysisReviewThread,
    )
    from src.core.models.recovery_models import RecoveryDraftCapture, RecoveryDraftInfo
    from src.core.models.guided_analysis_models import GuidedAnalysisProgress, GuidedAnalysisStage
    from src.core.models.parsing_models import StatConfig
    from src.core.models.quality_models import ColumnQuality, DataQualityReport

    from ring5._export import export_bytes, export_file
    from ring5._parse import ParseJob, ParseResult, ParserPlaygroundJob
    from ring5._scan import ScanJob
    from ring5._portfolio import render_portfolio
    from ring5._render import render_figure
    from ring5._dashboard import render_dashboard
    from ring5._linked_selection import apply_linked_selection
    from ring5._small_multiples import render_small_multiples
    from ring5._session import PlotType, Session, available_plot_types
    from ring5.shapers import available_shaper_types
    from ring5.coordinates import grouped_bar_coordinates
    from ring5.data import DrillDownResult, Table, read_table
    from ring5.decorations import FigureDecorations

try:
    __version__ = version("ring5")
except PackageNotFoundError:  # not installed (e.g. vendored checkout)
    __version__ = "0.0.0"


# Heavy exports (they pull pandas/matplotlib/plotly/the web rendering stack)
# resolved lazily: attribute name -> (module, attribute).
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AccessibilityFinding": ("src.core.models.accessibility_models", "AccessibilityFinding"),
    "AccessibilityReport": ("src.core.models.accessibility_models", "AccessibilityReport"),
    "AnalysisReport": ("src.core.models.report_models", "AnalysisReport"),
    "AnalysisRecipe": ("src.core.models.recipe_models", "AnalysisRecipe"),
    "AnalysisRecipeInfo": ("src.core.models.recipe_models", "AnalysisRecipeInfo"),
    "AnalysisRecipeMatrixCase": (
        "src.core.models.recipe_matrix_models",
        "AnalysisRecipeMatrixCase",
    ),
    "AnalysisRecipeMatrixResult": (
        "src.core.models.recipe_matrix_models",
        "AnalysisRecipeMatrixResult",
    ),
    "AnalysisRecipeRunResult": ("src.core.models.recipe_models", "AnalysisRecipeRunResult"),
    "BackgroundJobInfo": ("src.core.models.background_job_models", "BackgroundJobInfo"),
    "BackgroundJobLogEntry": ("src.core.models.background_job_models", "BackgroundJobLogEntry"),
    "FigureTheme": ("src.core.models.figure_theme_models", "FigureTheme"),
    "ImportColumn": ("src.core.models.import_models", "ImportColumn"),
    "ImportColumnCorrection": ("src.core.models.import_models", "ImportColumnCorrection"),
    "ImportOptions": ("src.core.models.import_models", "ImportOptions"),
    "ImportPreview": ("src.core.models.import_models", "ImportPreview"),
    "ImportRejectedRow": ("src.core.models.import_models", "ImportRejectedRow"),
    "EnvironmentComparison": ("src.core.models.environment_models", "EnvironmentComparison"),
    "EnvironmentDifference": ("src.core.models.environment_models", "EnvironmentDifference"),
    "EnvironmentMetadata": ("src.core.models.environment_models", "EnvironmentMetadata"),
    "Session": ("ring5._session", "Session"),
    "PlotType": ("ring5._session", "PlotType"),
    "available_plot_types": ("ring5._session", "available_plot_types"),
    "ParseJob": ("ring5._parse", "ParseJob"),
    "ParseResult": ("ring5._parse", "ParseResult"),
    "ParserPlaygroundJob": ("ring5._parse", "ParserPlaygroundJob"),
    "ParserPlaygroundResult": ("src.core.models.parsing_models", "ParserPlaygroundResult"),
    "PipelineConfigImportResult": ("src.core.models.data_models", "PipelineConfigImportResult"),
    "ScanJob": ("ring5._scan", "ScanJob"),
    "ScanResult": ("src.core.models.parsing_models", "ScanResult"),
    "ScannedVariable": ("src.core.models.parsing_models", "ScannedVariable"),
    "SourceInstance": ("src.core.models.parsing_models", "SourceInstance"),
    "render_figure": ("ring5._render", "render_figure"),
    "render_dashboard": ("ring5._dashboard", "render_dashboard"),
    "apply_linked_selection": ("ring5._linked_selection", "apply_linked_selection"),
    "render_small_multiples": ("ring5._small_multiples", "render_small_multiples"),
    "export_bytes": ("ring5._export", "export_bytes"),
    "export_file": ("ring5._export", "export_file"),
    "render_portfolio": ("ring5._portfolio", "render_portfolio"),
    "StatConfig": ("src.core.models.parsing_models", "StatConfig"),
    "RestoreReport": ("src.core.models.portfolio_models", "RestoreReport"),
    "ColumnQuality": ("src.core.models.quality_models", "ColumnQuality"),
    "DataQualityReport": ("src.core.models.quality_models", "DataQualityReport"),
    "ColumnContract": ("src.core.models.schema_contract_models", "ColumnContract"),
    "ColumnSemantics": ("src.core.models.semantic_metadata_models", "ColumnSemantics"),
    "DatasetInfo": ("src.core.models.dataset_workspace_models", "DatasetInfo"),
    "DatasetLineage": ("src.core.models.dataset_workspace_models", "DatasetLineage"),
    "DatasetRevision": ("src.core.models.dataset_workspace_models", "DatasetRevision"),
    "DatasetSnapshotInfo": ("src.core.models.dataset_workspace_models", "DatasetSnapshotInfo"),
    "DashboardSpec": ("src.core.models.visualization.dashboard_spec", "DashboardSpec"),
    "DrillDownResult": ("ring5.data", "DrillDownResult"),
    "DatasetSchemaContract": ("src.core.models.schema_contract_models", "DatasetSchemaContract"),
    "DatasetSemantics": ("src.core.models.semantic_metadata_models", "DatasetSemantics"),
    "JoinCardinality": ("src.core.models.dataset_workspace_models", "JoinCardinality"),
    "JoinDiagnostics": ("src.core.models.dataset_workspace_models", "JoinDiagnostics"),
    "LinkedSelectionSpec": (
        "src.core.models.visualization.linked_selection_spec",
        "LinkedSelectionSpec",
    ),
    "ConfigurationDifference": (
        "src.core.models.visualization.plot_configuration_comparison",
        "ConfigurationDifference",
    ),
    "PlotConfigurationComparison": (
        "src.core.models.visualization.plot_configuration_comparison",
        "PlotConfigurationComparison",
    ),
    "PlotTransferResult": (
        "src.core.models.visualization.plot_transfer_result",
        "PlotTransferResult",
    ),
    "PortfolioDiff": ("src.core.models.portfolio_revision_models", "PortfolioDiff"),
    "PortfolioDiffEntry": ("src.core.models.portfolio_revision_models", "PortfolioDiffEntry"),
    "PortfolioBundleArtifact": (
        "src.core.models.portfolio_bundle_models",
        "PortfolioBundleArtifact",
    ),
    "PortfolioBundleContents": (
        "src.core.models.portfolio_bundle_models",
        "PortfolioBundleContents",
    ),
    "PortfolioBundleInfo": ("src.core.models.portfolio_bundle_models", "PortfolioBundleInfo"),
    "PortfolioBundleResult": ("src.core.models.portfolio_bundle_models", "PortfolioBundleResult"),
    "PortfolioIntegrityReport": (
        "src.core.models.portfolio_integrity_models",
        "PortfolioIntegrityReport",
    ),
    "PortfolioIntegritySection": (
        "src.core.models.portfolio_integrity_models",
        "PortfolioIntegritySection",
    ),
    "PortfolioRevisionInfo": ("src.core.models.portfolio_revision_models", "PortfolioRevisionInfo"),
    "ReportFigure": ("src.core.models.report_models", "ReportFigure"),
    "ReportNarrative": ("src.core.models.report_models", "ReportNarrative"),
    "ReportProvenance": ("src.core.models.report_models", "ReportProvenance"),
    "ReportTable": ("src.core.models.report_models", "ReportTable"),
    "RecipeExport": ("src.core.models.recipe_models", "RecipeExport"),
    "RecipeParameter": ("src.core.models.recipe_models", "RecipeParameter"),
    "RecipePlot": ("src.core.models.recipe_models", "RecipePlot"),
    "RecipeSource": ("src.core.models.recipe_models", "RecipeSource"),
    "SmallMultiplesSpec": (
        "src.core.models.visualization.small_multiples_spec",
        "SmallMultiplesSpec",
    ),
    "SchemaValidationReport": ("src.core.models.schema_contract_models", "SchemaValidationReport"),
    "SchemaViolation": ("src.core.models.schema_contract_models", "SchemaViolation"),
    "ScheduledReportResult": ("src.core.models.scheduled_report_models", "ScheduledReportResult"),
    "ShaperStepConfig": ("src.core.models.shaper_models", "ShaperStepConfig"),
    "WorkspaceSearchResponse": (
        "src.core.models.workspace_search_models",
        "WorkspaceSearchResponse",
    ),
    "WorkspaceSearchResult": ("src.core.models.workspace_search_models", "WorkspaceSearchResult"),
    "WorkspaceCommand": ("src.core.models.workspace_command_models", "WorkspaceCommand"),
    "WorkspaceCommandSearchResponse": (
        "src.core.models.workspace_command_models",
        "WorkspaceCommandSearchResponse",
    ),
    "WorkspaceArtifact": ("src.core.models.workspace_metadata_models", "WorkspaceArtifact"),
    "WorkspaceArtifactResponse": (
        "src.core.models.workspace_metadata_models",
        "WorkspaceArtifactResponse",
    ),
    "AnalysisReviewEvent": ("src.core.models.analysis_review_models", "AnalysisReviewEvent"),
    "AnalysisReviewResponse": ("src.core.models.analysis_review_models", "AnalysisReviewResponse"),
    "AnalysisReviewTarget": ("src.core.models.analysis_review_models", "AnalysisReviewTarget"),
    "AnalysisReviewTargetResponse": (
        "src.core.models.analysis_review_models",
        "AnalysisReviewTargetResponse",
    ),
    "AnalysisReviewThread": ("src.core.models.analysis_review_models", "AnalysisReviewThread"),
    "RecoveryDraftCapture": ("src.core.models.recovery_models", "RecoveryDraftCapture"),
    "RecoveryDraftInfo": ("src.core.models.recovery_models", "RecoveryDraftInfo"),
    "GuidedAnalysisProgress": ("src.core.models.guided_analysis_models", "GuidedAnalysisProgress"),
    "GuidedAnalysisStage": ("src.core.models.guided_analysis_models", "GuidedAnalysisStage"),
    "available_shaper_types": ("ring5.shapers", "available_shaper_types"),
    # Self-contained figure-scripting surface (so scripts import only `ring5`):
    "grouped_bar_coordinates": ("ring5.coordinates", "grouped_bar_coordinates"),
    "FigureDecorations": ("ring5.decorations", "FigureDecorations"),
    "Table": ("ring5.data", "Table"),
    "read_table": ("ring5.data", "read_table"),
}


def __getattr__(name: str) -> Any:
    """PEP 562 lazy resolution of the heavy public names."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(target[0]), target[1])
    globals()[name] = value  # cache: subsequent accesses skip __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


def shutdown() -> None:
    # [impl->req~ring5.api.process-lifecycle~1]
    """Drain accepted file tasks, then release their Perl worker processes.

    The pools restart on the next parse/scan. Both register interpreter-exit
    cleanup, so explicit shutdown releases resources early in long-running scripts.

    Raises:
        JobError: The caller cannot safely drain or close the worker pools.
    """
    from src.parsing.framework.work_pool import WorkPool
    from src.parsing.gem5.impl.strategies.perl_worker_pool import shutdown_worker_pool

    try:
        with WorkPool.get_instance().shutdown_scope():
            shutdown_worker_pool()
    except RuntimeError as exc:
        raise JobError(f"Unable to shut down worker pools: {exc}") from exc


__all__ = [
    "__version__",
    # workflow
    "Session",
    "AccessibilityFinding",
    "AccessibilityReport",
    "AnalysisReport",
    "AnalysisRecipe",
    "AnalysisRecipeInfo",
    "AnalysisRecipeMatrixCase",
    "AnalysisRecipeMatrixResult",
    "AnalysisRecipeRunResult",
    "BackgroundJobInfo",
    "BackgroundJobLogEntry",
    "FigureTheme",
    "ImportColumn",
    "ImportColumnCorrection",
    "ImportOptions",
    "ImportPreview",
    "ImportRejectedRow",
    "EnvironmentComparison",
    "EnvironmentDifference",
    "EnvironmentMetadata",
    "PlotType",
    "available_plot_types",
    "available_shaper_types",
    "StatConfig",
    "ParseJob",
    "ParseResult",
    "ParserPlaygroundJob",
    "ParserPlaygroundResult",
    "PipelineConfigImportResult",
    "ScanJob",
    "ScanResult",
    "ScannedVariable",
    "SourceInstance",
    "ShaperStepConfig",
    "RestoreReport",
    "ColumnQuality",
    "ColumnContract",
    "ColumnSemantics",
    "DataQualityReport",
    "DatasetInfo",
    "DatasetLineage",
    "DatasetRevision",
    "DatasetSnapshotInfo",
    "DashboardSpec",
    "DrillDownResult",
    "DatasetSchemaContract",
    "DatasetSemantics",
    "JoinCardinality",
    "JoinDiagnostics",
    "LinkedSelectionSpec",
    "ConfigurationDifference",
    "PlotConfigurationComparison",
    "PlotTransferResult",
    "PortfolioDiff",
    "PortfolioDiffEntry",
    "PortfolioBundleArtifact",
    "PortfolioBundleContents",
    "PortfolioBundleInfo",
    "PortfolioBundleResult",
    "PortfolioIntegrityReport",
    "PortfolioIntegritySection",
    "PortfolioRevisionInfo",
    "ReportFigure",
    "ReportNarrative",
    "ReportProvenance",
    "ReportTable",
    "RecipeExport",
    "RecipeParameter",
    "RecipePlot",
    "RecipeSource",
    "SmallMultiplesSpec",
    "SchemaValidationReport",
    "SchemaViolation",
    "ScheduledReportResult",
    "WorkspaceSearchResponse",
    "WorkspaceSearchResult",
    "WorkspaceCommand",
    "WorkspaceCommandSearchResponse",
    "WorkspaceArtifact",
    "WorkspaceArtifactResponse",
    "AnalysisReviewEvent",
    "AnalysisReviewResponse",
    "AnalysisReviewTarget",
    "AnalysisReviewTargetResponse",
    "AnalysisReviewThread",
    "RecoveryDraftCapture",
    "RecoveryDraftInfo",
    "GuidedAnalysisProgress",
    "GuidedAnalysisStage",
    "render_figure",
    "render_dashboard",
    "apply_linked_selection",
    "render_small_multiples",
    "export_bytes",
    "export_file",
    "render_portfolio",
    # typed figure config
    "FigureSpec",
    "DualAxisOpts",
    "LegendOpts",
    "ReferenceLineOpts",
    "grouped_bar_coordinates",
    "FigureDecorations",
    "Table",
    "read_table",
    # process utilities
    "doctor",
    "DoctorReport",
    "DependencyStatus",
    "shutdown",
    # errors
    "Ring5Error",
    "ScanError",
    "ParseError",
    "MissingStatError",
    "PipelineError",
    "ColumnNotFoundError",
    "DataLoadError",
    "DataValidationError",
    "RenderError",
    "PortfolioError",
    "PortfolioVersionError",
    "RecipeError",
    "JobError",
    "ExportError",
    "DependencyMissingError",
]
