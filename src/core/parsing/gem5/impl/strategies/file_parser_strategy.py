"""
File Parser Strategy Interface - Protocol Definition.

Defines the contract for gem5 file parsing strategies, enabling pluggable
implementations for different gem5 output formats and parsing workflows.

This interface supports a three-phase parsing workflow:
1. get_work_items(): Discover files to parse
2. execute(): Parse files and extract statistics
3. post_process(): Aggregate and transform results

Strategy Pattern Implementation:
Different strategies (SimpleStatsStrategy, ConfigAwareStrategy) can handle
various gem5 configurations, versions, and output formats while maintaining
a unified interface for the parsing service layer.
"""

from typing import Any, Dict, List, Protocol, Sequence

from src.core.models import StatConfig
from src.core.parsing.gem5.impl.pool.parse_work import ParseWork


class FileParserStrategy(Protocol):
    """
    Protocol defining the contract for file parsing strategies.

    A file parser strategy is responsible for:
    - Discovering gem5 statistics files
    - Extracting specified variables from those files
    - Aggregating results across multiple simulation runs

    Implementations:
        - SimpleStatsStrategy: Basic stats.txt parsing
        - ConfigAwareStrategy: Stats + config.ini parsing

    Usage Example:
        >>> strategy = SimpleStatsStrategy()
        >>> work_items = strategy.get_work_items("/sim/output", "stats.txt", variables)
        >>> results = strategy.execute("/sim/output", "stats.txt", variables)
        >>> final_results = strategy.post_process(results)

    Note: This uses Protocol (structural typing) rather than ABC (nominal typing)
    for flexibility and to support duck typing patterns common in Python.
    """

    def execute(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig]
    ) -> List[Dict[str, Any]]:
        """
        Execute the complete parsing workflow.

        Discovers files, parses them, and returns raw results. This is the
        main entry point for synchronous parsing operations.

        Args:
            stats_path: Root directory containing gem5 simulation outputs
            stats_pattern: Glob pattern for file matching (e.g., "stats.txt")
            variables: List of StatConfig objects defining what to extract

        Returns:
            List of dictionaries containing parsed statistics for each file

        Example:
            >>> results = strategy.execute("/sim/run1", "stats.txt", variables)
            >>> [{'system.cpu.ipc': 1.5, 'sim_path': '/sim/run1/stats.txt'}, ...]
        """
        ...

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig]
    ) -> Sequence[ParseWork]:
        """
        Discover and prepare work items for parallel execution.

        Scans the directory tree and returns ParseWork objects representing
        individual parsing tasks. Used by the work pool for parallel processing.

        Args:
            stats_path: Root directory to scan
            stats_pattern: File pattern to match
            variables: Variables to parse (used for preprocessing/validation)

        Returns:
            Sequence of ParseWork objects ready for pool submission

        Example:
            >>> work_items = strategy.get_work_items("/sim", "stats.txt", vars)
            >>> len(work_items)  # Number of files found
            15
        """
        ...

    def post_process(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post-process and aggregate raw parsing results.

        Performs transformations, enrichment, or aggregation on the raw
        results from execute(). For example, ConfigAwareStrategy augments
        results with data from config.ini files.

        Args:
            results: Raw results from execute() or parallel workers

        Returns:
            Processed and potentially enriched results

        Example:
            >>> raw_results = [{'ipc': 1.5, 'sim_path': '/sim/run1/stats.txt'}]
            >>> enriched = strategy.post_process(raw_results)
            >>> enriched[0].keys()
            dict_keys(['ipc', 'sim_path', 'config_data', ...])
        """
        ...
