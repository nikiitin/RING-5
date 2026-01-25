import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from src.common.types import StatTypeRegistry
from src.parsing.workers import ParseWorkPool

logger = logging.getLogger(__name__)


class Gem5StatsParser:
    """
    Ingestion engine for gem5 statistics.

    Coordinates parallel parsing of stats.txt files and maintains a unified
    registry of variables for analysis.
    """

    _instance: Optional["Gem5StatsParser"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[Dict[str, Any]],
        output_dir: str,
    ):
        """
        Initialize the parser with simulation context.

        Args:
            stats_path: Base directory containing simulation folders.
            stats_pattern: Filename pattern (e.g., 'stats.txt').
            variables: List of variable configurations defining what to extract.
            output_dir: Directory where results will be persisted.
        """
        self._stats_path = stats_path
        self._stats_pattern = stats_pattern
        self._variables = variables
        self._output_dir = output_dir
        self._results: List[Dict[str, Any]] = []
        self._var_names: List[str] = []

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
        Execute the full parsing workflow.

        Returns:
            Absolute path to the generated CSV file, or None if no files were processed.
        """
        self._parse_stats()
        return self._persist_results()

    def _map_variables(self) -> Dict[str, Any]:
        """
        Convert raw dictionary configurations into typed Stat objects.

        Handles multi-ID mapping (e.g., regex variables matching multiple controllers).
        """
        var_map: Dict[str, Any] = {}

        for var in self._variables:
            # Domain Layer #4: Use 'name' as primary key for internal mapping
            name = var.get("name") or var.get("id")
            if not name:
                raise ValueError("PARSER: Variable config missing 'name' or 'id'.")

            # Registry Inversion: Extract type-specific entries
            var_type = var["type"]
            if name in var_map:
                raise RuntimeError(f"PARSER: Duplicate variable definition: {name}")

            # Build kwargs for type creation (DTO Pattern)
            kwargs = {"repeat": var.get("repeat", 1)}

            # Registry Inversion: Extract type-specific entries
            if var_type == "vector":
                kwargs["entries"] = var.get("vectorEntries") or var.get("entries")
            elif var_type == "distribution":
                kwargs["minimum"] = var.get("minimum", 0)
                kwargs["maximum"] = var.get("maximum", 100)
                kwargs["statistics"] = var.get("vectorEntries") or var.get("statistics")
            elif var_type == "histogram":
                kwargs["bins"] = var.get("bins", 0)
                kwargs["max_range"] = var.get("max_range", 0.0)
                kwargs["entries"] = var.get("entries")
                kwargs["statistics"] = var.get("statistics") or var.get("vectorEntries")
            elif var_type == "configuration":
                kwargs["onEmpty"] = var.get("onEmpty", "None")

            # Instantiate Typed Stat (Strategy Pattern via Registry)
            stat_obj = StatTypeRegistry.create(var_type, **kwargs)
            var_map[name] = stat_obj

            # Handle multi-ID mapping (Variables matched via regex scanning)
            # This allows multiple physical IDs in stats.txt to contribute to
            # one logical variable (Sacred Scanning rule).
            parsed_ids = var.get("parsed_ids", [])
            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = stat_obj

        return var_map

    def _get_files(self) -> List[str]:
        """Find all stats files matching the pattern in the target path."""
        # Use scientific path resolution
        base = Path(self._stats_path)
        pattern = f"**/{self._stats_pattern}"
        files = [str(f) for f in base.glob(pattern)]
        logger.info(f"PARSER: Found {len(files)} candidate files in {self._stats_path}")
        return files

    def _parse_stats(self) -> None:
        """Parse all discovered stats files using the parallel ParseWorkPool."""
        from src.parsing.workers import Gem5ParseWork

        files = self._get_files()
        if not files:
            logger.warning(f"PARSER: No files found matching '{self._stats_pattern}'")
            return

        var_map = self._map_variables()
        self._var_names = [v.get("name") or v.get("id", "") for v in self._variables]

        pool = ParseWorkPool.get_instance()
        pool.start_pool()

        logger.info("PARSER: Queueing simulation data for digestion...")
        for file_path in tqdm(files, desc="Queueing"):
            pool.add_work(Gem5ParseWork(file_path, var_map))

        logger.info("PARSER: Waiting for parallel worker completion...")
        self._results = pool.get_results()

    def _persist_results(self) -> Optional[str]:
        """
        Transform parsed results into a structured CSV file.

        This handles the final normalization (balancing) and reduction of data.
        """
        if not self._results:
            return None

        # Presentation Layer Logic: Build header and record column layout
        header_parts: List[str] = []
        sample = self._results[0]
        column_map: Dict[str, Optional[List[str]]] = {}

        for var_name in self._var_names:
            if var_name not in sample:
                logger.error(f"PARSER: Critical variable '{var_name}' missing in results.")
                continue

            var = sample[var_name]

            # Use polymorphism to get entries (Scientific Reproducibility)
            entries = var.entries
            if entries:
                column_map[var_name] = entries
                header_parts.extend(f"{var_name}..{e}" for e in entries)
            else:
                column_map[var_name] = None
                header_parts.append(var_name)

        # File Handling (Data Layer)
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(self._output_dir, "results.csv")
        logger.info(f"PARSER: Persisting {len(self._results)} rows to {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(",".join(header_parts) + "\n")

            for file_stats in self._results:
                row_parts: List[str] = []
                for var_name in self._var_names:
                    if var_name not in file_stats:
                        # Zero Hallucination: Log missing data instead of guessing 0
                        logger.warning(f"PARSER: Variable '{var_name}' missing for simulation.")
                        row_parts.append("NaN")
                        continue

                    var = file_stats[var_name]
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

                f.write(",".join(row_parts) + "\n")

        return output_path


class ParserBuilder:
    """
    Fluent builder for Gem5StatsParser.

    Encapsulates configuration logic away from the core execution engine.
    """

    def __init__(self):
        """Initialize with sensible scientific defaults."""
        self._stats_path: str = ""
        self._stats_pattern: str = "stats.txt"
        self._variables: List[Dict[str, Any]] = []

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

    def with_variable(self, name: str, var_type: str, **kwargs) -> "ParserBuilder":
        """Define a single metric to extract."""
        var = {"name": name, "type": var_type, **kwargs}
        self._variables.append(var)
        return self

    def with_variables(self, variables: List[Dict[str, Any]]) -> "ParserBuilder":
        """Apply a bulk list of variable definitions."""
        self._variables.extend(variables)
        return self

    def with_output(self, output_dir: str) -> "ParserBuilder":
        """Set destination for the generated results.csv."""
        self._output_dir = output_dir
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

        with Gem5StatsParser._lock:
            Gem5StatsParser._instance = Gem5StatsParser(
                stats_path=self._stats_path,
                stats_pattern=self._stats_pattern,
                variables=self._variables,
                output_dir=self._output_dir,
            )
        return Gem5StatsParser._instance
