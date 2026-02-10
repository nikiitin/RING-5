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
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.core.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy

logger = logging.getLogger(__name__)


class ConfigAwareStrategy(SimpleStatsStrategy):
    """
    Advanced parsing strategy that ingests both stats.txt and config.ini.

    This strategy inherits from SimpleStatsStrategy to reuse the core stats
    parsing logic, but augments the results with metadata extracted from
    the gem5 configuration file found in the same directory.
    """

    def post_process(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Augment results with config data.
        """
        augmented_results = []
        for sim_result in results:
            if "sim_path" not in sim_result:
                # Should not happen if worker is correct, but safety first
                augmented_results.append(sim_result)
                continue

            sim_dir = Path(sim_result["sim_path"]).parent
            config_path = sim_dir / "config.ini"

            if config_path.exists():
                logger.debug(f"PARSER: Found config at {config_path}")
                config_data = self._parse_config(config_path)
                # Merge config data into result
                # Here we assume we add a 'config' dictionary.
                sim_result["config"] = config_data
            else:
                logger.warning(f"PARSER: config.ini not found for {sim_result['sim_path']}")

            augmented_results.append(sim_result)

        return augmented_results

    def _parse_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Parse the config.ini file.

        Returns:
            Dictionary representation of the config.
        """
        parser = configparser.ConfigParser()
        try:
            parser.read(str(config_path))
            # Convert ConfigParser to dict for easier handling
            return {section: dict(parser.items(section)) for section in parser.sections()}
        except Exception as e:
            logger.error(f"PARSER: Failed to parse {config_path}: {e}")
            return {}
