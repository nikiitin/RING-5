"""
RING-5 Core Models -- Shared data models and protocols for cross-layer communication.

These types form the "common language" between the parsing,
application-API, and presentation layers. They are intentionally kept
outside any single layer so that every module can depend on them
without introducing circular or upward imports.

Public API:
    - ScannedVariable: Metadata for a variable discovered in a stats file
    - StatConfig:      Configuration for a specific statistic extraction
    - PortfolioData:   TypedDict for session serialization/restoration
    - PlotProtocol:    Protocol defining the core plot interface
    - PlotDeserializer: Callable type alias for plot dict → PlotProtocol
"""

from src.core.models.data_models import (
    CacheStatsEntry,
    CacheStatsInfo,
    ColumnInfoResult,
    CsvMetadata,
    CsvPoolEntry,
    ParseVariableConfig,
    PipelineStep,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.accessibility_models import AccessibilityFinding, AccessibilityReport
from src.core.models.figure_theme_models import FigureTheme, FigureThemeContext
from src.core.models.environment_models import (
    EnvironmentComparison,
    EnvironmentDifference,
    EnvironmentMetadata,
)
from src.core.models.shaper_models import ShaperStepConfig, SplitApplyGroupConfig
from src.core.models.history_models import OperationRecord
from src.core.models.import_models import (
    ImportColumn,
    ImportColumnCorrection,
    ImportOptions,
    ImportPreview,
    ImportRejectedRow,
)
from src.core.models.browser_upload_models import BrowserUpload
from src.core.models.quality_models import ColumnQuality, DataQualityReport
from src.core.models.report_models import (
    AnalysisReport,
    ReportFigure,
    ReportNarrative,
    ReportProvenance,
    ReportTable,
)
from src.core.models.remote_source_models import (
    HttpSource,
    RemoteDownload,
    RemoteSourcePolicy,
    S3Source,
    SshSource,
)
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
from src.core.models.parsing_models import (
    IncrementalParseBatchResult,
    IncrementalParseResult,
    ParserPlaygroundBatchResult,
    ParserPlaygroundResult,
    ParseBatchResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)
from src.core.models.plot_protocol import PlotDeserializer, PlotProtocol
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.drill_down_result import DrillDownResult
from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.core.models.visualization.small_multiples_spec import FacetPanel, SmallMultiplesSpec
from src.core.models.visualization.plot_transfer_result import PlotTransferMode, PlotTransferResult
from src.core.models.visualization.plot_configuration_comparison import (
    ConfigurationChange,
    ConfigurationDifference,
    PlotConfigurationComparison,
)
from src.core.models.portfolio_models import PortfolioData, RestoreReport
from src.core.models.shaper_models import (
    BaseShaperConfig,
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    ItemSelectorConfig,
    MeanShaperConfig,
    NormalizeShaperConfig,
    SortShaperConfig,
    SplitApplyShaperConfig,
    TransformerShaperConfig,
)

__all__ = [
    "AccessibilityFinding",
    "AccessibilityReport",
    "AnalysisReport",
    "BaseShaperConfig",
    "CacheStatsEntry",
    "CacheStatsInfo",
    "ColumnInfoResult",
    "ColumnSelectorConfig",
    "ColumnQuality",
    "ColumnContract",
    "ColumnSemantics",
    "ConditionSelectorConfig",
    "CsvMetadata",
    "CsvPoolEntry",
    "DataQualityReport",
    "FigureTheme",
    "ImportColumn",
    "ImportColumnCorrection",
    "ImportOptions",
    "ImportPreview",
    "ImportRejectedRow",
    "HttpSource",
    "BrowserUpload",
    "FigureThemeContext",
    "DashboardSpec",
    "DrillDownResult",
    "EnvironmentComparison",
    "EnvironmentDifference",
    "EnvironmentMetadata",
    "DatasetInfo",
    "DatasetLineage",
    "DatasetRevision",
    "DatasetSnapshotInfo",
    "DatasetSchemaContract",
    "DatasetSemantics",
    "ItemSelectorConfig",
    "JoinDiagnostics",
    "JoinCardinality",
    "LinkedSelectionSpec",
    "FacetPanel",
    "SmallMultiplesSpec",
    "PlotTransferMode",
    "PlotTransferResult",
    "ConfigurationChange",
    "ConfigurationDifference",
    "PlotConfigurationComparison",
    "MeanShaperConfig",
    "NormalizeShaperConfig",
    "IncrementalParseBatchResult",
    "IncrementalParseResult",
    "ParserPlaygroundBatchResult",
    "ParserPlaygroundResult",
    "ParseBatchResult",
    "ParseVariableConfig",
    "PipelineStep",
    "SavedConfigData",
    "SavedConfigEntry",
    "ScanFileResult",
    "ScanResult",
    "ScannedVariable",
    "ScannedVariableDict",
    "SchemaValidationReport",
    "SchemaViolation",
    "ShaperStepConfig",
    "SortShaperConfig",
    "SplitApplyGroupConfig",
    "SplitApplyShaperConfig",
    "StatConfig",
    "TransformerShaperConfig",
    "PortfolioData",
    "RestoreReport",
    "ReportFigure",
    "ReportNarrative",
    "ReportProvenance",
    "ReportTable",
    "RemoteDownload",
    "RemoteSourcePolicy",
    "S3Source",
    "SshSource",
    "PlotProtocol",
    "PlotDeserializer",
    "OperationRecord",
]
