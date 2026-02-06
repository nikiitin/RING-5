"""
Base interfaces for the Parser layer.
Defines the Strategy pattern for data ingestion.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import StatConfig


class ParserStrategy(ABC):
    """
    Abstract strategy for parsing gem5 statistics files.

    Implementations should handle specific file formats (txt, json, etc.).
    """

    @abstractmethod
    def parse(
        self, stats_path: str, stats_pattern: str, variables: List[StatConfig], output_dir: str
    ) -> Optional[str]:
        """
        Execute the parsing workflow.

        Args:
            stats_path: Base directory for stats files.
            stats_pattern: Filename pattern.
            variables: Strongly-typed list of statistics to extract.
            output_dir: Destination for results.csv.

        Returns:
            Path to the generated results file, or None.
        """
        pass
