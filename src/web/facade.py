"""
RING-5 Backend Facade
Simplified interface to all backend operations (Facade Pattern).
Decouples the web interface from complex backend implementations.
"""

import datetime
import glob
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class BackendFacade:
    """
    Facade providing simplified access to all backend operations.
    Hides complexity of data parsing, processing, and storage.
    """

    def __init__(self):
        """Initialize the facade with persistent storage paths."""
        self.ring5_data_dir = Path(__file__).parent.parent.parent / ".ring5"
        self.csv_pool_dir = self.ring5_data_dir / "csv_pool"
        self.config_pool_dir = self.ring5_data_dir / "saved_configs"

        # Ensure directories exist
        self.csv_pool_dir.mkdir(parents=True, exist_ok=True)
        self.config_pool_dir.mkdir(parents=True, exist_ok=True)

    # ==================== CSV Pool Management ====================

    def load_csv_pool(self) -> List[Dict[str, Any]]:
        """
        Load list of CSV files in the pool, checking if they still exist.

        Returns:
            List of dicts with 'path', 'name', 'size', 'modified' keys
        """
        pool = []
        if self.csv_pool_dir.exists():
            for csv_file in sorted(
                self.csv_pool_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True
            ):
                pool.append(
                    {
                        "path": str(csv_file),
                        "name": csv_file.name,
                        "size": csv_file.stat().st_size,
                        "modified": csv_file.stat().st_mtime,
                    }
                )
        return pool

    def add_to_csv_pool(self, csv_path: str) -> str:
        """
        Add a CSV file to the pool with timestamp.

        Args:
            csv_path: Path to the CSV file to add

        Returns:
            Path to the file in the pool
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pool_path = self.csv_pool_dir / f"parsed_{timestamp}.csv"
        shutil.copy(csv_path, pool_path)
        return str(pool_path)

    def delete_from_csv_pool(self, csv_path: str) -> bool:
        """
        Delete a CSV file from the pool.

        Args:
            csv_path: Path to the CSV file to delete

        Returns:
            True if deleted successfully
        """
        try:
            Path(csv_path).unlink()
            return True
        except Exception:
            return False

    def load_csv_file(self, csv_path: str) -> pd.DataFrame:
        """
        Load a CSV file with automatic separator detection.

        Args:
            csv_path: Path to the CSV file

        Returns:
            DataFrame with the CSV data
        """
        # Use pandas' automatic separator detection
        return pd.read_csv(csv_path, sep=None, engine="python")

    # ==================== Configuration Management ====================

    def load_saved_configs(self) -> List[Dict[str, Any]]:
        """
        Load list of saved configuration files.

        Returns:
            List of dicts with 'path', 'name', 'modified', 'description' keys
        """
        configs = []
        if self.config_pool_dir.exists():
            for config_file in sorted(
                self.config_pool_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
            ):
                try:
                    with open(config_file, "r") as f:
                        config_data = json.load(f)
                    configs.append(
                        {
                            "path": str(config_file),
                            "name": config_file.name,
                            "modified": config_file.stat().st_mtime,
                            "description": config_data.get("description", "No description"),
                        }
                    )
                except (OSError, json.JSONDecodeError):
                    pass
        return configs

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: List[Dict],
        csv_path: Optional[str] = None,
    ) -> str:
        """
        Save a configuration to the pool.

        Args:
            name: Configuration name
            description: Configuration description
            shapers_config: List of shaper configurations
            csv_path: Optional path to associated CSV file

        Returns:
            Path to the saved configuration file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        config_filename = f"{name}_{timestamp}.json"
        config_path = self.config_pool_dir / config_filename

        config_data = {
            "name": name,
            "description": description,
            "timestamp": timestamp,
            "shapers": shapers_config,
            "csv_path": csv_path,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        return str(config_path)

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """
        Load a configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        with open(config_path, "r") as f:
            return json.load(f)

    def delete_configuration(self, config_path: str) -> bool:
        """
        Delete a configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if deleted successfully
        """
        try:
            Path(config_path).unlink()
            return True
        except Exception:
            return False

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
        from src.data_parser.src.dataParserFactory import DataParserFactory

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
        parser_vars = []
        for var in variables:
            var_config = {"id": var["name"], "type": var["type"]}

            # DEBUG
            print(f"DEBUG FACADE: Processing {var['name']} ({var['type']})")
            if var["type"] == "vector":
                print(f"  Has vectorEntries: {'vectorEntries' in var}")

            # Add type-specific parameters
            if var["type"] == "vector":
                if "vectorEntries" in var:
                    var_config["vectorEntries"] = var["vectorEntries"]
                else:
                    # Require vectorEntries for vectors
                    print(f"ERROR FACADE: Missing vectorEntries for {var['name']}")
                    raise ValueError(
                        f"Vector variable '{var['name']}' requires vectorEntries to be specified"
                    )

            elif var["type"] == "distribution":
                var_config["minimum"] = var.get("minimum", 0)
                var_config["maximum"] = var.get("maximum", 100)

            elif var["type"] == "configuration":
                var_config["onEmpty"] = var.get("onEmpty", "None")

            # Optional repeat parameter
            if "repeat" in var:
                var_config["repeat"] = var["repeat"]

            parser_vars.append(var_config)

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

        from src.data_parser.parser_params import DataParserParams

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
            progress_callback(4, 0.9, "Finalizing results...")

        # Return CSV path
        csv_path = Path(output_dir) / "results.csv"

        if csv_path.exists():
            if progress_callback:
                progress_callback(5, 1.0, "Parsing complete!")
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
        from src.data_plotter.src.shaper.shaperFactory import ShaperFactory

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

    # ==================== Data Managers ====================

    def apply_seeds_reducer(
        self, data: pd.DataFrame, categorical_cols: List[str], statistic_cols: List[str]
    ) -> pd.DataFrame:
        """
        Apply Seeds Reducer using the existing DataManager implementation.

        Args:
            data: Input DataFrame with random_seed column
            categorical_cols: Columns to group by
            statistic_cols: Numeric columns to calculate statistics for

        Returns:
            DataFrame with seeds reduced (mean and std dev calculated)
        """

        from src.data_management.dataManager import DataManager
        from src.data_management.impl.seedsReducer import SeedsReducer
        from src.data_management.manager_params import SeedsReducerParams

        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            data.to_csv(tmp_path, index=False)

        try:
            # Reset DataManager class variables (fresh state)
            DataManager._df_data = None
            DataManager._categorical_columns_data = None
            DataManager._statistic_columns_data = None
            DataManager._csvPath_data = None

            # Create proper params using SeedsReducerParams
            params = SeedsReducerParams(
                csv_path=tmp_path,
                categorical_columns=categorical_cols,
                statistic_columns=statistic_cols,
                enable_reduction=True,
            )

            # JSON config for SeedsReducer
            json_config = {"seedsReducer": True}

            # Create and execute manager
            reducer = SeedsReducer(params, json_config)
            reducer.manage()

            # Get result
            result_df = DataManager._df.copy()
            return result_df

        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

    def apply_outlier_remover(
        self, data: pd.DataFrame, outlier_column: str, categorical_cols: List[str]
    ) -> pd.DataFrame:
        """
        Apply Outlier Remover using the existing DataManager implementation.

        Args:
            data: Input DataFrame
            outlier_column: Column to check for outliers
            categorical_cols: Columns to group by for Q3 calculation

        Returns:
            DataFrame with outliers removed (values > Q3)
        """

        from src.data_management.dataManager import DataManager
        from src.data_management.impl.outlierRemover import OutlierRemover
        from src.data_management.manager_params import OutlierRemoverParams

        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            data.to_csv(tmp_path, index=False)

        try:
            # Reset DataManager class variables
            DataManager._df_data = None
            DataManager._categorical_columns_data = None
            DataManager._statistic_columns_data = None
            DataManager._csvPath_data = None

            # Create proper params using PreprocessorParams
            params = OutlierRemoverParams(
                csv_path=tmp_path,
                categorical_columns=categorical_cols,
                outlier_column=outlier_column,
                group_by_columns=categorical_cols,
            )

            # JSON config for OutlierRemover
            json_config = {"outlierStat": outlier_column}

            # Create and execute manager
            remover = OutlierRemover(params, json_config)
            remover.manage()

            # Get result
            result_df = DataManager._df.copy()
            return result_df

        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

    def apply_preprocessor(
        self, data: pd.DataFrame, operation: str, src_col1: str, src_col2: str, dst_col: str
    ) -> pd.DataFrame:
        """
        Apply Preprocessor using the existing DataManager implementation.

        Args:
            data: Input DataFrame
            operation: 'divide' or 'sum'
            src_col1: First source column
            src_col2: Second source column
            dst_col: Destination column name

        Returns:
            DataFrame with new column added
        """

        from src.data_management.dataManager import DataManager
        from src.data_management.impl.preprocessor import Preprocessor
        from src.data_management.manager_params import PreprocessorParams

        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            data.to_csv(tmp_path, index=False)

        try:
            # Reset DataManager class variables
            DataManager._df_data = None
            DataManager._categorical_columns_data = None
            DataManager._statistic_columns_data = None
            DataManager._csvPath_data = None

            # Auto-detect categorical columns
            categorical_cols = data.select_dtypes(include=["object"]).columns.tolist()

            # Create proper params using PreprocessorParams
            params = PreprocessorParams(
                csv_path=tmp_path,
                categorical_columns=categorical_cols,
                operations={dst_col: {"operator": operation, "src1": src_col1, "src2": src_col2}},
            )

            # JSON config for Preprocessor
            json_config = {
                "preprocessor": {
                    dst_col: {"operator": operation, "src1": src_col1, "src2": src_col2}
                }
            }

            # Create and execute manager
            processor = Preprocessor(params, json_config)
            processor.manage()

            # Get result
            result_df = DataManager._df.copy()
            return result_df

        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

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

            from src.data_parser.stats_scanner import StatsScanner

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
            files_to_scan = files[:limit]

            for file_path in files_to_scan:
                file_vars = StatsScanner.scan_file(str(file_path))
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

            return list(merged_vars.values())
        except Exception as e:
            print(f"Error scanning stats: {e}")
            return []

    def scan_vector_entries(
        self, stats_path: str, vector_name: str, file_pattern: str = "stats.txt"
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
            # Actually, let's just use StatsScanner but we can optimize it later if needed.
            # Or better: read lines and only regex match if line starts with vector_name.

            # Simple optimization: check if line starts with vector name
            # This avoids running complex regex on every line
            prefix = f"{vector_name}::"

            for file_path in files:
                try:
                    with open(file_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith(prefix):
                                # Extract entry name: name::ENTRY value...
                                # entry is between :: and space
                                parts = line.split("::", 1)
                                if len(parts) > 1:
                                    rest = parts[1]
                                    entry = rest.split()[0]
                                    all_entries.add(entry)
                except (OSError, UnicodeDecodeError):
                    continue

            return sorted(list(all_entries))

        except Exception as e:
            print(f"Error scanning vector entries: {e}")
            return []
