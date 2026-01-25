"""
gem5 Stats Parser

Main entry point for parsing gem5 statistics files.
Provides singleton access and builder pattern for configuration.
"""

import glob
import os
import threading
from typing import Dict, List, Optional

from tqdm import tqdm

from src.common.types import StatTypeRegistry
from src.parsing.workers import ParseWorkPool


class Gem5StatsParser:
    """
    Singleton parser for gem5 statistics files.

    Usage::

        parser = (Gem5StatsParser.builder()
            .with_path("/path/to/stats")
            .with_pattern("stats.txt")
            .with_variable("simTicks", "scalar")
            .with_output("/tmp/output")
            .build())
        parser.parse()

        # Or get existing instance
        parser = Gem5StatsParser.get_instance()
    """

    _instance: Optional["Gem5StatsParser"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: List[Dict],
        output_dir: str,
    ):
        self._stats_path = stats_path
        self._stats_pattern = stats_pattern
        self._variables = variables
        self._output_dir = output_dir
        self._results: List = []
        self._var_names: List[str] = []

    @classmethod
    def get_instance(cls) -> Optional["Gem5StatsParser"]:
        """Get the singleton instance (may be None if not configured)."""
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton and related managers."""
        with cls._lock:
            cls._instance = None
        ParseWorkPool.reset()

    @classmethod
    def builder(cls) -> "ParserBuilder":
        """Create a new parser builder."""
        return ParserBuilder()

    def parse(self) -> Optional[str]:
        """
        Parse stats files and generate CSV.

        Returns:
            Path to generated CSV file, or None if no results.
        """
        self._parse_stats()
        return self._write_csv()

    def _map_variables(self) -> Dict:
        """Map variable configs to typed stat objects."""
        var_map = {}

        for var in self._variables:
            name = var.get("name") or var.get("id")
            var_type = var["type"]
            repeat = var.get("repeat", 1)

            if name in var_map:
                raise RuntimeError(f"Duplicate variable: {name}")

            # Build kwargs for type creation
            kwargs = {"repeat": repeat}

            if var_type == "vector":
                entries = var.get("vectorEntries") or var.get("entries")
                if not entries:
                    raise ValueError(f"Vector '{name}' requires entries")
                kwargs["entries"] = entries

            elif var_type == "distribution":
                kwargs["minimum"] = var.get("minimum", 0)
                kwargs["maximum"] = var.get("maximum", 100)

            elif var_type == "histogram":
                if "bins" in var:
                    kwargs["bins"] = var["bins"]
                if "max_range" in var:
                    kwargs["max_range"] = var["max_range"]
                if "entries" in var or "vectorEntries" in var:
                    kwargs["entries"] = var.get("entries") or var.get("vectorEntries")

            elif var_type == "configuration":
                kwargs["onEmpty"] = var.get("onEmpty", "None")

            var_map[name] = StatTypeRegistry.create(var_type, **kwargs)

            # Handle multi-ID mapping for reduction
            parsed_ids = var.get("parsed_ids", [])
            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = var_map[name]

        return var_map

    def _get_files(self) -> List[str]:
        """Find stats files matching pattern."""
        pattern = f"{self._stats_path}/**/{self._stats_pattern}"
        files = glob.glob(pattern, recursive=True)
        print(f"Found {len(files)} files in {self._stats_path}")
        return files

    def _parse_stats(self) -> None:
        """Parse all stats files in parallel."""
        # Import here to avoid circular imports
        from src.parsing.workers import Gem5ParseWork

        files = self._get_files()
        if not files:
            print(f"Warning: No files found matching {self._stats_pattern}")
            return

        var_map = self._map_variables()
        self._var_names = [v.get("name") or v.get("id") for v in self._variables]

        pool = ParseWorkPool.get_instance()
        pool.start_pool()

        print("Adding files to parse...")
        for file in tqdm(files):
            pool.add_work(Gem5ParseWork(file, var_map))

        print("Parsing files...")
        self._results = pool.get_results()

    def _write_csv(self) -> Optional[str]:
        """Write results to CSV file."""
        if not self._results:
            return None

        # Build header and record column layout
        header_parts = []
        sample = self._results[0]
        column_map = {} # var_name -> List[entry_keys]

        for var_name in self._var_names:
            var = sample[var_name]
            var_type = type(var).__name__

            if var_type in ("Vector", "Distribution", "Histogram"):
                entries = var.entries
                column_map[var_name] = entries
                header_parts.extend(f"{var_name}..{e}" for e in entries)
            else:
                column_map[var_name] = None
                header_parts.append(var_name)

        # Write output
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(self._output_dir, "results.csv")
        print(f"Writing: {output_path}")

        with open(output_path, "w") as f:
            f.write(",".join(header_parts) + "\n")

            for file_stats in self._results:
                row_parts = []
                for var_name in self._var_names:
                    var = file_stats[var_name]
                    var.balance_content()
                    var.reduce_duplicates()
                    
                    entries = column_map[var_name]
                    if entries is not None:
                        # Fixed collection: use entries from header to pull data
                        reduced = var.reduced_content
                        for e in entries:
                            val = reduced.get(e, 0)
                            row_parts.append(str(val))
                    else:
                        row_parts.append(str(var.reduced_content))

                f.write(",".join(row_parts) + "\n")

        return output_path


class ParserBuilder:
    """Builder for configuring Gem5StatsParser."""

    def __init__(self):
        self._stats_path: str = ""
        self._stats_pattern: str = "stats.txt"
        self._variables: List[Dict] = []
        import tempfile

        self._output_dir: str = os.path.join(tempfile.gettempdir(), "gem5_output")

    def with_path(self, path: str) -> "ParserBuilder":
        """Set stats directory path."""
        self._stats_path = path
        return self

    def with_pattern(self, pattern: str) -> "ParserBuilder":
        """Set file pattern (default: stats.txt)."""
        self._stats_pattern = pattern
        return self

    def with_variable(self, name: str, var_type: str, **kwargs) -> "ParserBuilder":
        """Add a variable to parse."""
        var = {"name": name, "type": var_type, **kwargs}
        self._variables.append(var)
        return self

    def with_variables(self, variables: List[Dict]) -> "ParserBuilder":
        """Add multiple variables at once."""
        self._variables.extend(variables)
        return self

    def with_output(self, output_dir: str) -> "ParserBuilder":
        """Set output directory."""
        self._output_dir = output_dir
        return self

    def build(self) -> Gem5StatsParser:
        """Build and return the parser singleton."""
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
