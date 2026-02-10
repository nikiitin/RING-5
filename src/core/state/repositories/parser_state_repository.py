"""
Parser State Repository
Single Responsibility: Manage gem5 parser configuration and state.
"""

import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ParserStateRepository:
    """
    Repository for managing gem5 parser state and configuration.

    Responsibilities:
    - Manage parse variable configurations
    - Store stats file path and pattern
    - Track scanned variables from stats files
    - Manage parser enable/disable state

    Adheres to SRP: Only manages parser-related state in memory.
    """

    # Default variables for new sessions
    DEFAULT_PARSE_VARIABLES = [
        {"name": "simTicks", "type": "scalar", "_id": str(uuid.uuid4())},
        {"name": "benchmark_name", "type": "configuration", "_id": str(uuid.uuid4())},
        {"name": "config_description", "type": "configuration", "_id": str(uuid.uuid4())},
    ]

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Initialize default state
        self._parse_variables: List[Dict[str, Any]] = self.DEFAULT_PARSE_VARIABLES.copy()
        self._stats_path: str = "/path/to/gem5/stats"
        self._stats_pattern: str = "stats.txt"
        self._scanned_variables: List[Dict[str, Any]] = []
        self._use_parser: bool = False
        self._parser_strategy: str = "simple"

    def get_parse_variables(self) -> List[Dict[str, Any]]:
        """
        Get the list of variables to parse from gem5 stats.

        Returns:
            List of parse variable configurations
        """
        return self._parse_variables

    def set_parse_variables(self, variables: List[Dict[str, Any]]) -> None:
        """
        Set the parse variable list, ensuring each has a unique ID.

        Args:
            variables: List of variable configurations
        """
        # Ensure all variables have unique IDs
        for var in variables:
            if "_id" not in var:
                var["_id"] = str(uuid.uuid4())

        self._parse_variables = variables
        logger.info(f"PARSER_REPO: Parse variables updated - {len(variables)} variables")

    def add_parse_variable(self, variable: Dict[str, Any]) -> None:
        """
        Add a new variable to the parse list.

        Args:
            variable: Variable configuration to add
        """
        self._parse_variables.append(variable)
        self.set_parse_variables(self._parse_variables)

    def remove_parse_variable(self, variable_id: str) -> bool:
        """
        Remove a variable by its ID.

        Args:
            variable_id: UUID of variable to remove

        Returns:
            True if variable was removed, False if not found
        """
        initial_count = len(self._parse_variables)
        self._parse_variables = [v for v in self._parse_variables if v.get("_id") != variable_id]

        if len(self._parse_variables) < initial_count:
            return True
        return False

    def get_stats_path(self) -> str:
        """
        Get the gem5 stats file path pattern.

        Returns:
            Path pattern (e.g., "/path/to/gem5/stats")
        """
        return self._stats_path

    def set_stats_path(self, path: str) -> None:
        """
        Set the gem5 stats file path pattern.

        Args:
            path: Path pattern for stats files
        """
        self._stats_path = path
        logger.info(f"PARSER_REPO: Stats path set to '{path}'")

    def get_stats_pattern(self) -> str:
        """
        Get the stats filename pattern.

        Returns:
            Filename pattern (e.g., "stats.txt")
        """
        return self._stats_pattern

    def set_stats_pattern(self, pattern: str) -> None:
        """
        Set the stats filename pattern.

        Args:
            pattern: Filename pattern for stats files
        """
        self._stats_pattern = pattern
        logger.info(f"PARSER_REPO: Stats pattern set to '{pattern}'")

    def get_scanned_variables(self) -> List[Dict[str, Any]]:
        """
        Get variables discovered via scanning stats files.

        Returns:
            List of scanned variable metadata
        """
        return self._scanned_variables

    def set_scanned_variables(self, variables: List[Dict[str, Any]]) -> None:
        """
        Set the scanned variables list.

        Args:
            variables: List of scanned variable metadata
        """
        self._scanned_variables = variables
        logger.info(f"PARSER_REPO: Scanned variables updated - {len(variables)} variables")

    def is_using_parser(self) -> bool:
        """
        Check if parser mode is enabled.

        Returns:
            True if parser should be used for data ingestion
        """
        return self._use_parser

    def set_using_parser(self, use_parser: bool) -> None:
        """
        Enable or disable parser mode.

        Args:
            use_parser: True to enable parser, False to disable
        """
        self._use_parser = use_parser
        logger.info(f"PARSER_REPO: Parser mode {'enabled' if use_parser else 'disabled'}")

    def get_parser_strategy(self) -> str:
        """
        Get the current parsing strategy ('simple' or 'config_aware').

        Returns:
            Current strategy string
        """
        return self._parser_strategy

    def set_parser_strategy(self, strategy: str) -> None:
        """
        Set the current parsing strategy.

        Args:
            strategy: Strategy name ('simple' or 'config_aware')
        """
        self._parser_strategy = strategy.lower()
        logger.info(f"PARSER_REPO: Parsing strategy set to '{strategy}'")

    def clear_parser_state(self) -> None:
        """Clear all parser-related state (except parse variables)."""
        self._scanned_variables = []
        self._use_parser = False
        logger.info("PARSER_REPO: Parser state cleared")
