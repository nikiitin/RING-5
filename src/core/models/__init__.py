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
from src.core.models.shaper_models import ShaperStepConfig, SplitApplyGroupConfig
from src.core.models.history_models import OperationRecord
from src.core.models.quality_models import ColumnQuality, DataQualityReport
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
    "DashboardSpec",
    "DrillDownResult",
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
    "PlotProtocol",
    "PlotDeserializer",
    "OperationRecord",
]
