"""
Portfolio data models.

Defines the PortfolioData TypedDict used for session serialization
and restoration across all layers.
"""

from typing import Any, TypedDict

from src.core.models.data_models import (
    ParseVariableConfig,
    ScannedVariableDict,
    ShaperStepConfig,
)
from src.core.models.history_models import OperationRecord


class PortfolioData(TypedDict, total=False):
    """
    Type definition for portfolio restoration data.

    Attributes:
        parse_variables: List of parser variable configurations
        stats_path: Base path to simulator stats files
        stats_pattern: Pattern for stats file naming
        csv_path: Path to processed CSV data
        use_parser: Whether parser mode is enabled
        scanned_variables: List of variables discovered by scanner
        data_csv: CSV string representation of data
        plots: List of plot configurations
        plot_counter: Current plot ID counter
        config: Application configuration dictionary
        manager_history: Rolling list of last 10 manager operations
        portfolio_history: Full list of operations performed in this portfolio
    """

    parse_variables: list[ParseVariableConfig]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: list[ScannedVariableDict]
    data_csv: str
    plots: list[dict[str, Any]]
    plot_counter: int
    config: dict[str, Any]
    shapers: list[ShaperStepConfig]
    manager_history: list[OperationRecord]
    portfolio_history: list[OperationRecord]
