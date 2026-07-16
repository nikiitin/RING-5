"""
File Parser Strategy Interface - Protocol Definition.

Defines the contract for gem5 file parsing strategies, enabling pluggable
implementations for different gem5 output formats and parsing workflows.

This interface supports an async parsing workflow:
1. get_work_items(): discover files to parse (ParseWork units for the pool)
2. post_process(): aggregate and transform the pool's results

Strategy Pattern Implementation:
Different strategies (SimpleStatsStrategy, ConfigAwareStrategy) can handle
various gem5 configurations, versions, and output formats while maintaining
a unified interface for the parsing service layer.
"""

from collections.abc import Sequence
from typing import Any, Protocol

from src.core.models import StatConfig
from src.parsing.gem5.impl.pool.parse_work import ParseWork

INTERNAL_SIM_PATH_KEY = "__ring5_internal_sim_path"


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
        >>> results = [f.result() for f in pool.submit_batch_async(list(work_items)).futures]
        >>> final_results = strategy.post_process(results)

    Note: This uses Protocol (structural typing) rather than ABC (nominal typing)
    for flexibility and to support duck typing patterns common in Python.
    """

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: list[StatConfig]
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
        raise NotImplementedError

    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        raise NotImplementedError
