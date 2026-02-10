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
"""

from src.core.models.config.config_manager import ConfigTemplateGenerator, ConfigValidator
from src.core.models.history_models import OperationRecord
from src.core.models.parsing_models import ParseBatchResult, ScannedVariable, StatConfig
from src.core.models.plot_protocol import PlotProtocol
from src.core.models.portfolio_models import PortfolioData

__all__ = [
    "ParseBatchResult",
    "ScannedVariable",
    "StatConfig",
    "PortfolioData",
    "PlotProtocol",
    "ConfigValidator",
    "ConfigTemplateGenerator",
    "OperationRecord",
]
