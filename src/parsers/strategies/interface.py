from typing import Any, Dict, List, Protocol, Sequence

from src.parsers.models import StatConfig
from src.parsers.workers.parse_work import ParseWork


class ParserStrategy(Protocol):
    """
    Protocol defining the contract for parsing strategies.

    A parsing strategy is responsible for ingesting files and extracting
    statistics according to the provided configuration.
    """

    def execute(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig]
    ) -> List[Dict[str, Any]]:
        """Execute the parsing Logic (synchronous)."""
        ...

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig]
    ) -> Sequence[ParseWork]:
        """Return a list of work items for parallel execution."""
        ...

    def post_process(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform any post-processing on aggregated results."""
        ...
