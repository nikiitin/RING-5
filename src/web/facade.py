"""
RING-5 Backend Facade
Simplified interface to all backend operations (Facade Pattern).
Decouples the web interface from complex backend implementations.

NOTE: CSV and Configuration management have been extracted to dedicated services.
This facade now delegates to those services for backward compatibility.
"""

import glob
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.web.services.config_service import ConfigService
from src.web.services.csv_pool_service import CsvPoolService
from src.web.services.paths import PathService


class BackendFacade:
    """
    Facade providing simplified access to all backend operations.
    Hides complexity of data parsing, processing, and storage.

    NOTE: For new code, prefer using the dedicated services directly:
    - CsvPoolService for CSV file management
    - ConfigService for configuration persistence
    """

    def __init__(self):
        """Initialize the facade with persistent storage paths."""
        self.ring5_data_dir = PathService.get_data_dir()
        self.csv_pool_dir = CsvPoolService.get_pool_dir()
        self.config_pool_dir = ConfigService.get_config_dir()

    # ==================== CSV Pool Management (delegates to CsvPoolService) ====================

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """Load list of CSV files in the pool."""
        return CsvPoolService.load_pool()

    def add_to_csv_pool(self, csv_path: str) -> str:
        """Add a CSV file to the pool with timestamp."""
        return CsvPoolService.add_to_pool(csv_path)

    def delete_from_csv_pool(self, csv_path: str) -> bool:
        """Delete a CSV file from the pool."""
        return CsvPoolService.delete_from_pool(csv_path)

    def load_csv_file(self, csv_path: str) -> pd.DataFrame:
        """Load a CSV file with automatic separator detection."""
        return CsvPoolService.load_csv_file(csv_path)

    # ==================== Configuration Management (delegates to ConfigService) ====================

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """Load list of saved configuration files."""
        return ConfigService.load_saved_configs()

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict],
        csv_path: Optional[str] = None,
    ) -> str:
        """Save a configuration to the pool."""
        return ConfigService.save_configuration(name, description, shapers_config, csv_path)

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load a configuration from file."""
        return ConfigService.load_configuration(config_path)

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return ConfigService.delete_configuration(config_path)

    # ==================== Data Parsing ====================

    def find_stats_files(self, stats_path: str, stats_pattern: str) -> List[str]:
        """
        Find gem5 stats files matching the pattern.

        Args:
            stats_path: Base directory path
            stats_pattern: File pattern (e.g., "stats.txt")

        Returns:
            List of file paths
        """
        pattern = f"{stats_path}/**/{stats_pattern}"
        return glob.glob(pattern, recursive=True)

    def parse_gem5_stats(
        self,
        stats_path: str,
        stats_pattern: str,
        compress: bool,
        variables: List[Dict],
        output_dir: str,
        progress_callback=None,
    ) -> Optional[str]:
        """
        Parse gem5 stats files and generate CSV.

        Args:
            stats_path: Base directory with stats files
            stats_pattern: File pattern to match
            compress: Enable compression
            variables: List of variable configurations
            output_dir: Output directory for results
            progress_callback: Optional callback function(step, progress, message)

        Returns:
            Path to generated CSV file or None
        """

        from src.parsing.factory import DataParserFactory

        # Reset parser factory to ensure new configuration is used
        DataParserFactory.reset()

        # Report progress
        if progress_callback:
            progress_callback(1, 0.1, "Initializing parser...")

        # Create parse config
        parse_config_data = {
            "outputPath": output_dir,
            "parseConfig": {"file": "webapp_parse", "config": "webapp_config"},
        }

        # Create configuration directory
        parse_component_dir = Path("config_files/json_components/parse")
        parse_component_dir.mkdir(parents=True, exist_ok=True)
        parse_config_file = parse_component_dir / "webapp_parse.json"

        # Map variables to parser format with type-specific parameters
        # AND Handle Regex Expansion for reduction candidates via parsed_ids
        parser_vars = []

        for var in variables:
            var_name = var["name"]

            # Helper to add variable without modification
            def _add_as_is(name, v):
                # Check for Alias
                alias = v.get("alias")

                if alias and alias.strip():
                    # Use Alias as ID, map original name via parsed_ids
                    cfg = {
                        "id": alias.strip(),
                        "type": v["type"],
                        "parsed_ids": [name],  # Map original name to this alias
                    }
                else:
                    # No alias, standard behavior
                    cfg = {"id": name, "type": v["type"]}

                # Add type-specific parameters
                if v["type"] == "vector":
                    if "vectorEntries" in v:
                        cfg["vectorEntries"] = v["vectorEntries"]
                        if "useSpecialMembers" in v:
                            cfg["useSpecialMembers"] = v["useSpecialMembers"]
                    else:
                        raise ValueError(
                            f"Vector variable '{name}' requires vectorEntries to be specified"
                        )

                elif v["type"] == "distribution":
                    cfg["minimum"] = v.get("minimum", 0)
                    cfg["maximum"] = v.get("maximum", 100)

                elif v["type"] == "configuration":
                    cfg["onEmpty"] = v.get("onEmpty", "None")

                if "repeat" in v:
                    cfg["repeat"] = v["repeat"]

                parser_vars.append(cfg)

            # Check if this variable looks like a regex pattern (contains \d+ or *)
            if "\\d+" in var_name or "*" in var_name:
                # Scan a few files to find concrete instances
                concrete_vars = self.scan_stats_variables(stats_path, stats_pattern, limit=3)

                matched_concrete_names = []
                for cv in concrete_vars:
                    if re.fullmatch(var_name, cv["name"]):
                        matched_concrete_names.append(cv["name"])

                if matched_concrete_names:
                    # Found concrete matches: Configure Parser for reduction.
                    # Create one variable entry mapping all concrete IDs via 'parsed_ids'.
                    count = len(matched_concrete_names)

                    # Create reduced variable config
                    reduced_config = {
                        "id": var_name,
                        "type": var["type"],
                        "parsed_ids": matched_concrete_names,
                        "repeat": count,  # Parser uses this for averaging
                    }

                    # Copy specific fields
                    if var["type"] == "vector":
                        if "vectorEntries" in var:
                            reduced_config["vectorEntries"] = var["vectorEntries"]
                        else:
                            reduced_config["vectorEntries"] = "total, mean"

                    elif var["type"] == "distribution":
                        reduced_config["minimum"] = var.get("minimum", -10)
                        reduced_config["maximum"] = var.get("maximum", 100)

                    elif var["type"] == "configuration":
                        reduced_config["onEmpty"] = var.get("onEmpty", "None")

                    parser_vars.append(reduced_config)

                else:
                    # No match found? Add as is
                    _add_as_is(var_name, var)
            else:
                # Normal variable
                _add_as_is(var_name, var)

        # Create parser configuration
        parser_config = [
            {
                "id": "webapp_config",
                "impl": "perl",
                "compress": "True" if compress else "False",
                "parsings": [{"path": stats_path, "files": stats_pattern, "vars": parser_vars}],
            }
        ]

        # Write configurations
        with open(parse_config_file, "w") as f:
            json.dump(parser_config, f, indent=2)

        config_file = Path(output_dir) / "config.json"
        with open(config_file, "w") as f:
            json.dump(parse_config_data, f, indent=2)

        if progress_callback:
            progress_callback(2, 0.2, "Configuring parser...")

        from src.parsing.params import DataParserParams

        parser_params = DataParserParams(config_json=parse_config_data)

        if progress_callback:
            if compress:
                progress_callback(3, 0.3, "Compressing files...")
            else:
                progress_callback(3, 0.5, "Parsing files...")

        # Run parser
        parser = DataParserFactory.getDataParser(parser_params, "perl")
        parser()

        if progress_callback:
            progress_callback(4, 1.0, "Parsing complete!")

        # Return CSV path (no post-processing reduction needed anymore)
        csv_path = Path(output_dir) / "results.csv"

        if csv_path.exists():
            return str(csv_path)

        return None

    # ==================== Data Processing ====================

    def apply_shapers(self, data: pd.DataFrame, shapers_config: List[Dict]) -> pd.DataFrame:
        """
        Apply data shapers to transform the data.

        Args:
            data: Input DataFrame
            shapers_config: List of shaper configurations

        Returns:
            Transformed DataFrame
        """
        from src.web.services.shapers.factory import ShaperFactory

        result = data.copy()

        for shaper_config in shapers_config:
            shaper_type = shaper_config["type"]
            shaper = ShaperFactory.createShaper(shaper_type, shaper_config)
            result = shaper(result)

        return result

    def get_column_info(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get information about DataFrame columns.

        Args:
            data: Input DataFrame

        Returns:
            Dictionary with column information
        """
        return {
            "total_columns": len(data.columns),
            "numeric_columns": data.select_dtypes(include=["number"]).columns.tolist(),
            "categorical_columns": data.select_dtypes(include=["object"]).columns.tolist(),
            "total_rows": len(data),
            "null_counts": data.isnull().sum().to_dict(),
        }

    # ==================== Parser Operations ====================

    def scan_stats_variables(
        self, stats_path: str, file_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Scan stats files to discover available variables.

        Args:
            stats_path: Directory containing stats files
            file_pattern: Pattern to match stats files
            limit: Maximum number of files to scan (default 5 for speed)

        Returns:
            List of discovered variables with types
        """
        # Import here to avoid circular imports if any
        try:
            # Add src to path if needed, though app.py does it
            import sys

            if str(Path(__file__).parent.parent.parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            # from src.parsing.stats_scanner import StatsScanner -> Removed in favor of Perl script

            # Find first matching file
            search_path = Path(stats_path)
            if not search_path.exists():
                return []

            files = list(search_path.rglob(file_pattern))
            if not files:
                return []

            # Scan limited files and merge results
            merged_vars = {}

            # Limit files for speed
            # Limit files for speed
            files_to_scan = files[:limit]

            # Use Parallel Scanner
            import shutil

            from src.scanning.impl.multiprocessing.scanWorkPool import ScanWorkPool
            from src.scanning.impl.multiprocessing.statsScanWork import StatsScanWork

            perl_exe = shutil.which("perl")
            if not perl_exe:
                # Should we raise? or just log and return empty?
                # Given the existing structure, logging seems appropriate as it returns [] on error
                print("Perl executable not found.")
                return []

            script_path = (
                self.ring5_data_dir.parent
                / "src/parsing/impl/data_parser_perl/src/parser_impl/statsScanner.pl"
            ).resolve()

            # Initialize Pool
            pool = ScanWorkPool.getInstance()

            # Submit Work
            for file_path in files_to_scan:
                work = StatsScanWork(file_path, perl_exe, script_path)
                pool.addWork(work)

            # Collect Results
            results = pool.getResults()

            # Merge Results
            for file_vars in results:
                for var in file_vars:
                    name = var["name"]
                    if name not in merged_vars:
                        merged_vars[name] = var
                    else:
                        # Merge entries if vector
                        if var["type"] == "vector" and "entries" in var:
                            existing_entries = set(merged_vars[name].get("entries", []))
                            new_entries = set(var["entries"])
                            if not new_entries.issubset(existing_entries):
                                merged_vars[name]["entries"] = sorted(
                                    list(existing_entries.union(new_entries))
                                )

            return sorted(list(merged_vars.values()), key=lambda x: x["name"])
        except Exception as e:
            print(f"Error scanning stats: {e}")
            return []

    def scan_stats_variables_with_grouping(
        self, stats_path: str, file_pattern: str = "stats.txt", limit: int = 5
    ) -> List[Dict[str, Any]]:
        r"""
        Scan and group variables using Regex (heuristic for reduction).
        e.g. system.cpu0.ipc and system.cpu1.ipc -> system.cpu\\d+.ipc
        """

        raw_vars = self.scan_stats_variables(stats_path, file_pattern, limit)
        if not raw_vars:
            return []

        # Grouping Logic
        # We look for numbers in the variable names and replace them with \d+
        grouped_vars = {}

        for var in raw_vars:
            name = var["name"]
            # Check if name contains numbers
            if re.search(r"\d+", name):
                # Create regex pattern
                pattern = re.sub(r"\d+", r"\\d+", name)

                if pattern not in grouped_vars:
                    grouped_vars[pattern] = {
                        "name": pattern,
                        "type": var["type"],
                        "entries": var.get("entries", []),
                        "count": 1,
                        "examples": [name],
                    }
                else:
                    grouped_vars[pattern]["count"] += 1
                    if len(grouped_vars[pattern]["examples"]) < 3:
                        grouped_vars[pattern]["examples"].append(name)

                    # Merge entries if needed
                    if "entries" in var:
                        existing = set(grouped_vars[pattern]["entries"])
                        new_entries = set(var["entries"])
                        grouped_vars[pattern]["entries"] = sorted(list(existing.union(new_entries)))

            else:
                # No numbers, keep as is
                if name not in grouped_vars:
                    grouped_vars[name] = var
                    grouped_vars[name]["count"] = 1
                    grouped_vars[name]["examples"] = [name]

        # Format results
        results = []
        for _, info in grouped_vars.items():
            # If we grouped multiple items, it's a pattern
            if info["count"] > 1:
                # It's a reduction candidate!
                # Ensure type is correct (should be same for all group members usually)
                results.append(info)
            else:
                # If count is 1, but it has \d+, it might be a single item that just has a number
                # If the original name matched the pattern (ignoring escaped backslashes), it's not a group
                # logic: if pattern == name (with escaping), it's just a variable with a number that isn't repeated?
                # Actually, if count == 1, we prefer original name
                if len(info["examples"]) == 1:
                    info["name"] = info["examples"][0]
                results.append(info)

        return sorted(results, key=lambda x: x["name"])

    def scan_vector_entries(
        self,
        stats_path: str,
        vector_name: str,
        file_pattern: str = "stats.txt",
        limit: int = 1000000,
    ) -> List[str]:
        """
        Scan ALL stats files for entries of a specific vector variable.
        Optimized to only look for the specific vector.

        Args:
            stats_path: Directory containing stats files
            vector_name: Name of the vector variable
            file_pattern: Pattern to match stats files

        Returns:
            List of all unique entries found for this vector
        """
        try:
            import sys

            if str(Path(__file__).parent.parent.parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            search_path = Path(stats_path)
            if not search_path.exists():
                return []

            files = list(search_path.rglob(file_pattern))
            if not files:
                return []

            all_entries = set()

            # We could optimize StatsScanner to accept a filter, but for now
            # scanning is reasonably fast per file, the overhead is opening many files.
            # To make it truly fast, we should use grep if available, but let's stick to python for
            # portability.
            # Limit files
            files_to_scan = files[:limit]

            # Use Parallel Scanner
            import shutil

            from src.scanning.impl.multiprocessing.scanWorkPool import ScanWorkPool
            from src.scanning.impl.multiprocessing.vectorScanWork import VectorScanWork

            script_path = (
                self.ring5_data_dir.parent
                / "src/parsing/impl/data_parser_perl/src/parser_impl/statsScanner.pl"
            ).resolve()

            perl_exe = shutil.which("perl")
            if not perl_exe:
                return []

            # Initialize Pool
            pool = ScanWorkPool.getInstance()

            # Submit Work
            for file_path in files_to_scan:
                work = VectorScanWork(file_path, vector_name, perl_exe, script_path)
                pool.addWork(work)

            # Collect Results
            results = pool.getResults()

            # Merge unique entries
            for entry_list in results:
                all_entries.update(entry_list)

            return sorted(list(all_entries))
        except Exception:
            return []
