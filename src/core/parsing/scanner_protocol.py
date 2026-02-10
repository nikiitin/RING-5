"""
Scanner Protocol - Simulator-agnostic scanning interface.

Defines the contract for all scanner implementations. Any simulator backend
(gem5, SST, etc.) must implement this Protocol to integrate with RING-5.
"""

from concurrent.futures import Future
from typing import List, Protocol

from src.core.models import ScannedVariable


class ScannerProtocol(Protocol):
    """
    Protocol defining the contract for scanning simulator output files.

    A scanner implementation handles:
    - Submitting async scan jobs for parallel variable discovery
    - Aggregating scan results from multiple files into a unified list

    Implementations:
        - Gem5Scanner: gem5 simulator stats scanning
    """

    @staticmethod
    def submit_scan_async(
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> List[Future[List[ScannedVariable]]]:
        """
        Submit async scanning job and return futures.

        Args:
            stats_path: Base directory to search for stats files
            stats_pattern: Filename pattern to match (default: "stats.txt")
            limit: Maximum number of files to scan (0 for unlimited)

        Returns:
            List of Future objects that will resolve to scan results

        Raises:
            FileNotFoundError: If stats_path doesn't exist or no files found
        """

    @staticmethod
    def aggregate_scan_results(
        results: List[List[ScannedVariable]],
    ) -> List[ScannedVariable]:
        """
        Aggregate results from async scan into unified variable list.

        Merges variables across files, deduplicates entries, and applies
        pattern aggregation.

        Args:
            results: List of scan results from each file

        Returns:
            Sorted list of merged variables with deduplicated entries
        """
