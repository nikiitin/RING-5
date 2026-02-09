"""
Portfolio data models.

Defines the PortfolioData TypedDict used for session serialization
and restoration across all layers.
"""

from typing import Any, Dict, List, TypedDict


class PortfolioData(TypedDict, total=False):
    """
    Type definition for portfolio restoration data.

    Attributes:
        parse_variables: List of parser variable configurations
        stats_path: Base path to gem5 stats files
        stats_pattern: Pattern for stats file naming
        csv_path: Path to processed CSV data
        use_parser: Whether gem5 parser mode is enabled
        scanned_variables: List of variables discovered by scanner
        data_csv: CSV string representation of data
        plots: List of plot configurations
        plot_counter: Current plot ID counter
        config: Application configuration dictionary
    """

    parse_variables: List[Dict[str, Any]]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: List[Dict[str, Any]]
    data_csv: str
    plots: List[Dict[str, Any]]
    plot_counter: int
    config: Dict[str, Any]
