"""
Gem5 Statistics Parser - Configurable Strategy-Based Ingestion Engine.

Coordinates the parsing of gem5 statistics files using pluggable parsing
strategies. Supports multiple output formats and automatically selects the
appropriate strategy based on file structure and user configuration.

Strategies:
- SimpleStatsStrategy: Basic line-by-line parsing for standard gem5 output
- ConfigAwareStrategy: Advanced parsing with gem5 configuration awareness

Features:
- Singleton instantiation with thread-safe initialization
- Variable type detection (scalar, vector, distribution, histogram)
- Parallel work pool execution for performance
- Progress tracking and error recovery
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from src.core.parsing.models import StatConfig
from src.core.parsing.strategies.config_aware import ConfigAwareStrategy
from src.core.parsing.strategies.interface import ParserStrategy
from src.core.parsing.strategies.simple import SimpleStatsStrategy
from src.core.parsing.workers import ParseWorkPool

logger = logging.getLogger(__name__)


class Gem5StatsParser:
    """
    Ingestion engine for gem5 statistics.

    Coordinates parsing using a configurable Strategy.
    """

    _instance: Optional["Gem5StatsParser"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[StatConfig],
        output_dir: str,
        strategy: ParserStrategy,
    ):
        """
        Initialize the parser with simulation context.

        Args:
            stats_path: Base directory containing simulation folders.
            stats_pattern: Filename pattern (e.g., 'stats.txt').
            variables: List of variable configurations defining what to extract.
            output_dir: Directory where results will be persisted.
            strategy: The parsing strategy to employ.
        """
        self._stats_path = stats_path
        self._stats_pattern = stats_pattern
        self._variables = variables
        self._output_dir = output_dir
        self._strategy = strategy
        self._results: List[Dict[str, Any]] = []
        self._var_names: List[str] = [v.name for v in variables]

    @classmethod
    def get_instance(cls) -> Optional["Gem5StatsParser"]:
        """Get the active parser instance."""
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton state and clear associated worker pools."""
        with cls._lock:
            cls._instance = None
        ParseWorkPool.reset()

    @classmethod
    def builder(cls) -> "ParserBuilder":
        """Create a new fluently-configured builder."""
        return ParserBuilder()

    def parse(self) -> Optional[str]:
        """
        Execute the full parsing workflow via the injected strategy.

        Returns:
            Absolute path to the generated CSV file, or None if no files were processed.
        """
        self._results = self._strategy.execute(
            self._stats_path, self._stats_pattern, self._variables
        )
        return self._persist_results()

    def _persist_results(self) -> Optional[str]:
        """
        Transform parsed results into a structured CSV file.

        This handles the final normalization (balancing) and reduction of data.
        """
        if not self._results:
            return None

        # Presentation Layer Logic: Build header and record column layout
        header_parts: List[str] = []
        # Fallback if results is empty or first item is weird, but we checked empty above
        sample = self._results[0]
        column_map: Dict[str, Optional[List[str]]] = {}

        for var_name in self._var_names:
            if var_name not in sample:
                # It's possible the strategy didn't find the var in the first sample
                # We still want to include it in the header
                # OR we accept that some vars might be missing entirely if config didn't match
                # For safety, we keep the original logic: only complain if it's missing in sample
                # But actually, the header should depend on CONFIG, not Sample for consistency.
                # However, to avoid breaking changes, we stick to existing logic for now.
                if var_name in sample:
                    pass  # handled below
                else:
                    # If missing in sample, we assume scalar/none for now or log error
                    pass

            # Check if present
            if var_name in sample:
                var = sample[var_name]
                # Use polymorphism to get entries (Scientific Reproducibility)
                if hasattr(var, "entries"):  # Check if it's a Stat object
                    entries = var.entries
                    if entries:
                        column_map[var_name] = entries
                        header_parts.extend(f"{var_name}..{e}" for e in entries)
                    else:
                        column_map[var_name] = None
                        header_parts.append(var_name)
                else:
                    # Might be raw data from Config strategy
                    column_map[var_name] = None
                    header_parts.append(var_name)
            else:
                # Missing variable handling for header?
                # Previous implementation skipped it. We stick to that.
                logger.error(f"PARSER: Critical variable '{var_name}' missing in results.")
                continue

        # File Handling (Data Layer)
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(self._output_dir, "results.csv")
        logger.info(f"PARSER: Persisting {len(self._results)} rows to {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(",".join(header_parts) + "\n")

            for file_stats in self._results:
                row_parts: List[str] = []
                for var_name in self._var_names:
                    if var_name not in column_map:
                        continue  # Skip variables that weren't in the header map

                    if var_name not in file_stats:
                        # Zero Hallucination: Log missing data instead of guessing 0
                        logger.warning(f"PARSER: Variable '{var_name}' missing for simulation.")
                        row_parts.append("NaN")
                        continue

                    var = file_stats[var_name]

                    # Handle Stat objects vs Raw Data
                    if hasattr(var, "balance_content"):
                        # Data Domain Layer: Finalize aggregations
                        var.balance_content()
                        var.reduce_duplicates()

                        entries = column_map[var_name]
                        if entries is not None:
                            reduced = var.reduced_content
                            for e in entries:
                                # Zero Hallucination: Use explicit string 'NaN' for missing buckets
                                val = reduced.get(e, "NaN")
                                row_parts.append(str(val))
                        else:
                            row_parts.append(str(var.reduced_content))
                    else:
                        # Raw data (e.g. string/int from config)
                        row_parts.append(str(var))

                f.write(",".join(row_parts) + "\n")

        return output_path


class ParserBuilder:
    """
    Fluent builder for Gem5StatsParser.

    Encapsulates configuration logic away from the core execution engine.
    """

    def __init__(self) -> None:
        """Initialize with sensible scientific defaults."""
        self._stats_path: str = ""
        self._stats_pattern: str = "stats.txt"
        self._variables: List[StatConfig] = []
        # Default strategy
        self._strategy_type: str = "simple"

        import tempfile

        self._output_dir: str = os.path.join(tempfile.gettempdir(), "ring5_output")

    def with_path(self, path: str) -> "ParserBuilder":
        """Set base directory for stats files."""
        self._stats_path = path
        return self

    def with_pattern(self, pattern: str) -> "ParserBuilder":
        """Set filename filter."""
        self._stats_pattern = pattern
        return self

    def with_variable(self, name: str, var_type: str, **kwargs: Any) -> "ParserBuilder":
        """Define a single metric to extract."""
        repeat = kwargs.pop("repeat", 1)
        statistics_only = kwargs.pop("statistics_only", False)
        var = StatConfig(
            name=name, type=var_type, repeat=repeat, statistics_only=statistics_only, params=kwargs
        )
        self._variables.append(var)
        return self

    def with_variables(self, variables: List[StatConfig | Dict[str, Any]]) -> "ParserBuilder":
        """Apply a bulk list of variable definitions."""
        for var in variables:
            if isinstance(var, dict):
                # Unpack dict and handle expected keys
                v_copy = var.copy()
                name = v_copy.pop("name")
                var_type = v_copy.pop("type")
                self.with_variable(name, var_type, **v_copy)
            else:
                self._variables.append(var)
        return self

    def with_output(self, output_dir: str) -> "ParserBuilder":
        """Set destination for the generated results.csv."""
        self._output_dir = output_dir
        return self

    def with_strategy(self, strategy_type: str) -> "ParserBuilder":
        """Set the parsing strategy ('simple' or 'config_aware')."""
        self._strategy_type = strategy_type.lower()
        return self

    def build(self) -> Gem5StatsParser:
        """
        Validate configuration and build the parser instance.

        Raises:
            ValueError: If critical configuration paths or variables are missing.
        """
        if not self._stats_path:
            raise ValueError("Stats path is required")
        if not self._variables:
            raise ValueError("At least one variable is required")

        # Select Strategy
        strategy: ParserStrategy
        if self._strategy_type == "simple":
            strategy = SimpleStatsStrategy()
        elif self._strategy_type == "config_aware":
            strategy = ConfigAwareStrategy()
        else:
            raise ValueError(f"Unknown strategy type: {self._strategy_type}")

        with Gem5StatsParser._lock:
            Gem5StatsParser._instance = Gem5StatsParser(
                stats_path=self._stats_path,
                stats_pattern=self._stats_pattern,
                variables=self._variables,
                output_dir=self._output_dir,
                strategy=strategy,
            )
        return Gem5StatsParser._instance
