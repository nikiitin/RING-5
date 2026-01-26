"""
Parse Service
Encapsulates logic for parsing gem5 stats files.
Coordinates the ParseWorkPool and handles result aggregation.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from src.parsers.type_mapper import TypeMapper
from src.parsers.workers.gem5_parse_work import Gem5ParseWork
from src.parsers.workers.pool import ParseWorkPool
from src.parsers.workers.parse_work import ParseWork

logger = logging.getLogger(__name__)


class ParseService:
    """Service for orchestrating the parsing workflow."""

    _active_var_names: List[str] = []

    @staticmethod
    def submit_parse_async(
        stats_path: str, stats_pattern: str, variables: List[Dict[str, Any]], output_dir: str
    ) -> List[Any]:
        """Submit async parsing job and return futures."""
        
        search_path = Path(stats_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        pattern = f"**/{stats_pattern}"
        files = [str(f) for f in search_path.glob(pattern)]
        
        if not files:
            raise FileNotFoundError(f"No files found matching {stats_pattern}")

        var_map = ParseService._map_variables(variables)
        ParseService._active_var_names = [v.get("name") or v.get("id", "") for v in variables]

        pool = ParseWorkPool.get_instance()
        # Reset pool futures if desired, or just submit new batch
        # For simplicity in this architecture, we submit and get specifically these futures
        batch_work = [Gem5ParseWork(str(file_path), var_map) for file_path in files]
        return pool.submit_batch_async(cast(List[ParseWork], batch_work))

    @staticmethod
    def cancel_parse() -> None:
        """Cancel current parse."""
        ParseWorkPool.get_instance().cancel_all()

    @staticmethod
    def construct_final_csv(output_dir: str, results: List[Any]) -> Optional[str]:
        """
        Aggregate provided results and save to CSV.
        """
        if not results:
            logger.warning("PARSER: No results to persist.")
            return None

        # Logic adapted from Gem5StatsParser._persist_results
        header_parts: List[str] = []
        sample = results[0]
        column_map: Dict[str, Optional[List[str]]] = {}
        
        # Use stored var names to ensure consistent order
        var_names = ParseService._active_var_names
        # Fallback if empty
        if not var_names:
            var_names = list(sample.keys())

        for var_name in var_names:
            if var_name not in sample:
                continue

            var = sample[var_name]
            entries = var.entries
            if entries:
                column_map[var_name] = entries
                header_parts.extend(f"{var_name}..{e}" for e in entries)
            else:
                column_map[var_name] = None
                header_parts.append(var_name)

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "results.csv")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(",".join(header_parts) + "\n")

            for file_stats in results:
                row_parts: List[str] = []
                for var_name in var_names:
                    if var_name not in file_stats:
                        row_parts.append("NaN")
                        continue

                    var = file_stats[var_name]
                    var.balance_content()
                    var.reduce_duplicates()

                    entries = column_map[var_name]
                    if entries is not None:
                        reduced = var.reduced_content
                        for e in entries:
                            val = reduced.get(e, "NaN")
                            row_parts.append(str(val))
                    else:
                        row_parts.append(str(var.reduced_content))

                f.write(",".join(row_parts) + "\n")

        return output_path

    @staticmethod
    def _map_variables(variables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Map configuration to Stat objects."""
        var_map: Dict[str, Any] = {}

        for var in variables:
            name = var.get("name") or var.get("id")
            if not name:
                continue

            stat_obj = TypeMapper.create_stat(var)
            var_map[name] = stat_obj

            parsed_ids = var.get("parsed_ids", [])
            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = stat_obj

        return var_map
