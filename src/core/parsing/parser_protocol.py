from concurrent.futures import Future
from typing import Any, Protocol, runtime_checkable

from src.core.models import ParseBatchResult, ScannedVariable, StatConfig


@runtime_checkable
class SimulationParser(Protocol):
    """
    Unified architectural protocol for simulation data parsing and variable scanning.

    Any class implementing this protocol can be injected into the Streamlit frontend
    or core Facade, decoupling the application from 'gem5' specifics.
    """

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParseBatchResult:
        """
        Submit an asynchronous parsing job over the simulation output files.
        """
        ...

    def finalize_parsing(
        self,
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Post-process and aggregate internal parsing results into a canonical format (e.g. CSV).
        """
        ...

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[list[ScannedVariable]]]:
        """
        Submit an async scanning job to discover potential variables across files.
        """
        ...

    def aggregate_scan_results(
        self,
        results: list[list[ScannedVariable]],
    ) -> list[ScannedVariable]:
        """
        Aggregate and deduplicate the variable scan results from workers.
        """
        ...
