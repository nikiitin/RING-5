"""
Parser State Repository
Single Responsibility: Manage gem5 parser configuration and state.
"""

import logging
import uuid
from typing import Any, Dict, List

import streamlit as st

logger = logging.getLogger(__name__)


class ParserStateRepository:
    """
    Repository for managing gem5 parser state and configuration.

    Responsibilities:
    - Manage parse variable configurations
    - Store stats file path and pattern
    - Track scanned variables from stats files
    - Manage parser enable/disable state

    Adheres to SRP: Only manages parser-related state, nothing else.
    """

    # State keys
    PARSE_VARIABLES_KEY = "parse_variables"
    STATS_PATH_KEY = "stats_path"
    STATS_PATTERN_KEY = "stats_pattern"
    SCANNED_VARIABLES_KEY = "scanned_variables"
    USE_PARSER_KEY = "use_parser"

    # Default variables for new sessions
    DEFAULT_PARSE_VARIABLES = [
        {"name": "simTicks", "type": "scalar", "_id": str(uuid.uuid4())},
        {"name": "benchmark_name", "type": "configuration", "_id": str(uuid.uuid4())},
        {"name": "config_description", "type": "configuration", "_id": str(uuid.uuid4())},
    ]

    @staticmethod
    def get_parse_variables() -> List[Dict[str, Any]]:
        """
        Get the list of variables to parse from gem5 stats.

        Returns:
            List of parse variable configurations
        """
        return st.session_state.get(
            ParserStateRepository.PARSE_VARIABLES_KEY,
            ParserStateRepository.DEFAULT_PARSE_VARIABLES.copy(),
        )

    @staticmethod
    def set_parse_variables(variables: List[Dict[str, Any]]) -> None:
        """
        Set the parse variable list, ensuring each has a unique ID.

        Args:
            variables: List of variable configurations
        """
        # Ensure all variables have unique IDs
        for var in variables:
            if "_id" not in var:
                var["_id"] = str(uuid.uuid4())

        st.session_state[ParserStateRepository.PARSE_VARIABLES_KEY] = variables
        logger.info(f"PARSER_REPO: Parse variables updated - {len(variables)} variables")

    @staticmethod
    def add_parse_variable(variable: Dict[str, Any]) -> None:
        """
        Add a new variable to the parse list.

        Args:
            variable: Variable configuration to add
        """
        variables = ParserStateRepository.get_parse_variables()
        variables.append(variable)
        ParserStateRepository.set_parse_variables(variables)

    @staticmethod
    def remove_parse_variable(variable_id: str) -> bool:
        """
        Remove a variable by its ID.

        Args:
            variable_id: UUID of variable to remove

        Returns:
            True if variable was removed, False if not found
        """
        variables = ParserStateRepository.get_parse_variables()
        initial_count = len(variables)
        variables = [v for v in variables if v.get("_id") != variable_id]

        if len(variables) < initial_count:
            ParserStateRepository.set_parse_variables(variables)
            return True
        return False

    @staticmethod
    def get_stats_path() -> str:
        """
        Get the gem5 stats file path pattern.

        Returns:
            Path pattern (e.g., "/path/to/gem5/stats")
        """
        return st.session_state.get(ParserStateRepository.STATS_PATH_KEY, "/path/to/gem5/stats")

    @staticmethod
    def set_stats_path(path: str) -> None:
        """
        Set the gem5 stats file path pattern.

        Args:
            path: Path pattern for stats files
        """
        st.session_state[ParserStateRepository.STATS_PATH_KEY] = path
        logger.info(f"PARSER_REPO: Stats path set to '{path}'")

    @staticmethod
    def get_stats_pattern() -> str:
        """
        Get the stats filename pattern.

        Returns:
            Filename pattern (e.g., "stats.txt")
        """
        return st.session_state.get(ParserStateRepository.STATS_PATTERN_KEY, "stats.txt")

    @staticmethod
    def set_stats_pattern(pattern: str) -> None:
        """
        Set the stats filename pattern.

        Args:
            pattern: Filename pattern for stats files
        """
        st.session_state[ParserStateRepository.STATS_PATTERN_KEY] = pattern
        logger.info(f"PARSER_REPO: Stats pattern set to '{pattern}'")

    @staticmethod
    def get_scanned_variables() -> List[Dict[str, Any]]:
        """
        Get variables discovered via scanning stats files.

        Returns:
            List of scanned variable metadata
        """
        return st.session_state.get(ParserStateRepository.SCANNED_VARIABLES_KEY, [])

    @staticmethod
    def set_scanned_variables(variables: List[Dict[str, Any]]) -> None:
        """
        Set the scanned variables list.

        Args:
            variables: List of scanned variable metadata
        """
        st.session_state[ParserStateRepository.SCANNED_VARIABLES_KEY] = variables
        logger.info(f"PARSER_REPO: Scanned variables updated - {len(variables)} variables")

    @staticmethod
    def is_using_parser() -> bool:
        """
        Check if parser mode is enabled.

        Returns:
            True if parser should be used for data ingestion
        """
        return st.session_state.get(ParserStateRepository.USE_PARSER_KEY, False)

    @staticmethod
    def set_using_parser(use_parser: bool) -> None:
        """
        Enable or disable parser mode.

        Args:
            use_parser: True to enable parser, False to disable
        """
        st.session_state[ParserStateRepository.USE_PARSER_KEY] = use_parser
        logger.info(f"PARSER_REPO: Parser mode {'enabled' if use_parser else 'disabled'}")

    @staticmethod
    def clear_parser_state() -> None:
        """Clear all parser-related state (except parse variables)."""
        st.session_state[ParserStateRepository.SCANNED_VARIABLES_KEY] = []
        st.session_state[ParserStateRepository.USE_PARSER_KEY] = False
        logger.info("PARSER_REPO: Parser state cleared")
