"""
Config Aware Strategy - Advanced Gem5 Parser with Metadata Extraction.

Extends SimpleStatsStrategy to automatically extract and integrate gem5
configuration metadata (config.ini) alongside statistics. Enriches parsed
data with system configuration context.

Features:
- Inherits base stats parsing from SimpleStatsStrategy
- Auto-discovers and parses config.ini in same directory
- Attaches configuration metadata to results
- Enables configuration-aware analysis and filtering
"""

import configparser
import json
import logging
from pathlib import Path
from typing import Any

from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY

logger = logging.getLogger(__name__)


class ConfigAwareStrategy(SimpleStatsStrategy):
    """
    Advanced parsing strategy that ingests both stats.txt and config.ini.

    This strategy inherits from SimpleStatsStrategy to reuse the core stats
    parsing logic, but augments the results with metadata extracted from
    the gem5 configuration file found in the same directory.
    """

    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Augment results with config data.
        """
        augmented_results: list[dict[str, Any]] = []
        for sim_result in results:
            if INTERNAL_SIM_PATH_KEY not in sim_result:
                raise RuntimeError("PARSER: config-aware result is missing simulation provenance.")
            if "sim_path" in sim_result or "config_json" in sim_result:
                raise ValueError(
                    "PARSER: config-aware metadata columns collide with requested statistics."
                )

            sim_path = str(sim_result[INTERNAL_SIM_PATH_KEY])
            sim_dir = Path(sim_path).parent
            config_path = sim_dir / "config.ini"

            if not config_path.is_file():
                raise FileNotFoundError(f"PARSER: config.ini not found beside {sim_path}")

            logger.debug("PARSER: Found config at %s", config_path)
            config_data = self._parse_config(config_path)
            public_result = {
                key: value for key, value in sim_result.items() if key != INTERNAL_SIM_PATH_KEY
            }
            public_result["sim_path"] = sim_path
            public_result["config_json"] = json.dumps(
                config_data, sort_keys=True, separators=(",", ":")
            )
            augmented_results.append(public_result)

        return augmented_results

    def _parse_config(self, config_path: Path) -> dict[str, Any]:
        """
        Parse the config.ini file.

        Returns:
            Dictionary representation of the config.
        """
        parser = configparser.ConfigParser()
        try:
            loaded = parser.read(str(config_path))
            if not loaded or not parser.sections():
                raise configparser.Error("configuration contains no sections")
            # Convert ConfigParser to dict for easier handling
            return {section: dict(parser.items(section)) for section in parser.sections()}
        except (configparser.Error, OSError) as e:
            logger.error("PARSER: Failed to parse %s: %s", config_path, e)
            raise RuntimeError(f"PARSER: Failed to parse {config_path}: {e}") from e
