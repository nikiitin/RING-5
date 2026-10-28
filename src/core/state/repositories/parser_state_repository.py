"""In-memory repository for simulator parser configuration."""

import logging
from copy import deepcopy

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.common.variable_identity import normalize_variable_ids

from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.parsing_models import ScannedVariable, default_parse_configs

logger = logging.getLogger(__name__)


class ParserStateRepository:
    """Store parser inputs, scan results, and selected variables."""

    # [impl->req~ring5.ingestion.parse-output-provenance~1]

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self.reset_to_defaults()

    def reset_to_defaults(self) -> None:
        """Replace configured inputs and scan results with independent parser defaults."""
        self._parse_variables: list[ParseVariableConfig] = normalize_variable_ids(
            [StatConfigCodec.to_draft(config) for config in default_parse_configs()]
        )
        self._stats_path: str = "/path/to/stats"
        self._stats_pattern: str = "stats.txt"
        self._scanned_variables: list[ScannedVariableDict] = []
        self._use_parser: bool = False
        self._parser_strategy: str = "simple"
        self._simulator: str = "gem5"

    def get_parse_variables(self) -> list[ParseVariableConfig]:
        """
        Get the list of variables to parse from simulator stats.

        Returns:
            A deep copy of the parse-variable list (defensive copy-on-read).
        """
        return deepcopy(self._parse_variables)

    def set_parse_variables(self, variables: list[ParseVariableConfig]) -> None:
        """
        Set the parse variable list, ensuring each has a unique ID.

        Entries are validated and copied: callers (notably portfolio restore)
        may pass untrusted or shared dicts, and injecting ``_id`` into
        caller-owned objects would alias repository state into them.

        Args:
            variables: List of variable configurations.

        Raises:
            TypeError: If any entry is not a dict (e.g. a plain string from a
                hand-edited portfolio) — callers that handle untrusted input
                filter first and report what they dropped.
        """
        copied = normalize_variable_ids(
            [StatConfigCodec.validate_draft(value) for value in variables]
        )
        self._parse_variables = copied
        logger.info("PARSER_REPO: Parse variables updated - %d variables", len(copied))

    def get_stats_path(self) -> str:
        """
        Get the stats file path pattern.

        Returns:
            Path pattern (e.g., "/path/to/stats")
        """
        return self._stats_path

    def set_stats_path(self, path: str) -> None:
        """
        Set the stats file path pattern.

        Args:
            path: Path pattern for stats files
        """
        if self._stats_path == path:
            return
        self._stats_path = path
        logger.info("PARSER_REPO: Stats path set to '%s'", path)

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
        if self._stats_pattern == pattern:
            return
        self._stats_pattern = pattern
        logger.info("PARSER_REPO: Stats pattern set to '%s'", pattern)

    def get_scanned_variables(self) -> list[ScannedVariableDict]:
        """
        Get variables discovered via scanning stats files.

        Returns:
            A deep copy of the scanned-variable list (defensive copy-on-read).
        """
        return deepcopy(self._scanned_variables)

    def set_scanned_variables(self, variables: list[ScannedVariableDict]) -> None:
        """
        Set the scanned variables list.

        Args:
            variables: List of scanned variable metadata
        """
        for variable in variables:
            ScannedVariable.from_dict(variable)
        self._scanned_variables = deepcopy(variables)
        logger.info("PARSER_REPO: Scanned variables updated - %d variables", len(variables))

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
        if self._use_parser == use_parser:
            return
        self._use_parser = use_parser
        logger.info("PARSER_REPO: Parser mode %s", "enabled" if use_parser else "disabled")

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
        normalized = strategy.lower()
        if self._parser_strategy == normalized:
            return
        self._parser_strategy = normalized
        logger.info("PARSER_REPO: Parsing strategy set to '%s'", strategy)

    def get_simulator(self) -> str:
        """
        Get the currently selected simulator backend.

        Returns:
            Simulator identifier (e.g., "gem5")
        """
        return self._simulator

    def set_simulator(self, simulator: str) -> None:
        """
        Set the simulator backend to use for parsing.

        Args:
            simulator: Simulator identifier (must be registered)
        """
        if self._simulator == simulator:
            return
        self._simulator = simulator
        logger.info("PARSER_REPO: Simulator set to '%s'", simulator)

    def clear_parser_state(self) -> None:
        """Clear scan results and parser mode while preserving configured inputs."""
        self._scanned_variables = []
        self._use_parser = False
        logger.info("PARSER_REPO: Parser state cleared")
