"""Standard strategy for parsing gem5 statistics files."""

from __future__ import annotations

import copy
import logging
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatType

from src.core.common.security_limits import (
    MAX_PARSE_FILES,
    MAX_PARSE_FILE_BYTES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_TOTAL_BYTES,
    MAX_PARSE_VARIABLES,
)
from src.core.common.safe_regex import SafeRegexError, numeric_pattern_id
from src.core.common.utils import sanitize_log_value
from src.core.models import StatConfig
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


def _max_var_repeat() -> int:
    """Per-variable cap on regex-expanded instances (``repeat``).

    A regex variable can match thousands of concrete instances (e.g. an NxN
    network traffic matrix → repeat in the thousands), which blows up memory when
    parsed across many files. Variables above this cap fail before worker
    submission rather than producing silently incomplete output. Override with
    ``RING5_MAX_VAR_REPEAT``; ``0`` disables the cap for trusted inputs.
    """
    raw = os.environ.get("RING5_MAX_VAR_REPEAT")
    if raw is not None:
        try:
            n = int(raw)
            if n >= 0:
                return n
            logger.warning("RING5_MAX_VAR_REPEAT=%r is negative; using default", raw)
        except ValueError:
            logger.warning("RING5_MAX_VAR_REPEAT=%r is not an integer; using default", raw)
    return 1024


class SimpleStatsStrategy:
    """
    Standard parsing strategy for gem5 stats.txt files.

    This strategy iterates through all files matching the pattern,
    submits them to the parallel worker pool, and aggregates the results.
    It corresponds to the legacy behavior of Gem5StatsParser.
    """

    # [impl->req~ring5.ingestion.simple-strategy~1]

    def get_work_items(
        self, stats_path: str, stats_pattern: str, variables: Sequence[StatConfig]
    ) -> Sequence[Gem5ParseWork]:
        """Return a list of work items for parallel execution.

        Each work item receives its own independent copy of the variable
        map so that concurrent threads cannot corrupt shared mutable
        ``StatType`` objects.
        """
        t_start = time.perf_counter()
        files = self._get_files(stats_path, stats_pattern)
        t_files = time.perf_counter()
        logger.info(f"PERF: File discovery (glob) took {t_files - t_start:.4f}s")

        # Build one template map, then deep-copy per file so that each
        # thread-based worker operates on its own mutable StatType set.
        t_map_start = time.perf_counter()
        template_map: dict[str, StatType] = self._map_variables(variables)
        if len(template_map) > MAX_PARSE_VARIABLES:
            raise RuntimeError(
                f"PARSER: {len(template_map)} logical variables and aliases exceed the "
                f"{MAX_PARSE_VARIABLES}-variable limit."
            )
        matrix_cells = len(files) * len(template_map)
        if matrix_cells > MAX_PARSE_MATRIX_CELLS:
            raise RuntimeError(
                f"PARSER: workload requires {matrix_cells} file-variable cells; "
                f"the limit is {MAX_PARSE_MATRIX_CELLS}. Reduce the file set or variables."
            )
        t_map_end = time.perf_counter()
        logger.info(f"PERF: Variable map creation took {t_map_end - t_map_start:.4f}s")

        t_copy_start = time.perf_counter()
        works = [Gem5ParseWork(str(file_path), copy.deepcopy(template_map)) for file_path in files]
        t_copy_end = time.perf_counter()
        logger.info(
            f"PERF: Total deepcopy cost for {len(files)} files: {t_copy_end - t_copy_start:.4f}s"
        )

        return works

    def post_process(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove worker-only provenance before writing the public CSV."""
        processed: list[dict[str, Any]] = []
        for result in results:
            public_result = dict(result)
            public_result.pop(INTERNAL_SIM_PATH_KEY, None)
            processed.append(public_result)
        return processed

    def _get_files(self, stats_path: str, stats_pattern: str) -> list[str]:
        """Find all stats files matching the pattern in the target path.

        Raises:
            FileNotFoundError: When no file matches — same contract as the
                scan path. Returning an empty work list instead would let a
                whole parse run "succeed" while producing nothing.
        """
        files = find_stats_files(stats_path, stats_pattern, raise_if_empty=True)
        if len(files) > MAX_PARSE_FILES:
            raise RuntimeError(
                f"PARSER: {len(files)} files exceed the {MAX_PARSE_FILES}-file parse limit."
            )

        total_bytes = 0
        for file_path in files:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_PARSE_FILE_BYTES:
                raise RuntimeError(
                    f"PARSER: input exceeds the {MAX_PARSE_FILE_BYTES // (1024 * 1024)} MiB "
                    f"per-file limit: {file_path}"
                )
            total_bytes += file_size
            if total_bytes > MAX_PARSE_TOTAL_BYTES:
                raise RuntimeError(
                    f"PARSER: selected inputs exceed the "
                    f"{MAX_PARSE_TOTAL_BYTES // (1024 * 1024 * 1024)} GiB aggregate limit."
                )
        logger.info(
            "PARSER: Found %d candidate files in %s",
            len(files),
            sanitize_log_value(stats_path),
        )
        return files

    def _map_variables(self, variables: Sequence[StatConfig]) -> dict[str, StatType]:
        """
        Convert configuration models into typed Stat objects.

        Handles multi-ID mapping (e.g., regex variables matching multiple controllers).
        """
        # [impl->req~ring5.ingestion.output-aliases~1]
        var_map: dict[str, StatType] = {}

        for var in variables:
            name = var.name
            # Validation logic kept from original parser
            if not name:
                raise ValueError("PARSER: Variable config missing 'name'.")
            if name == INTERNAL_SIM_PATH_KEY:
                raise ValueError(f"PARSER: Variable name {name!r} is reserved for internal use.")

            if name in var_map:
                raise RuntimeError(f"PARSER: Duplicate variable definition: {name}")

            # Handle multi-ID mapping (Variables matched via regex scanning)
            parsed_ids_raw = var.params.get("parsed_ids", [])
            if not isinstance(parsed_ids_raw, list) or any(
                not isinstance(pattern_id, str) or not pattern_id for pattern_id in parsed_ids_raw
            ):
                raise ValueError(
                    f"PARSER: parsed_ids for {name!r} must be a list of non-empty strings."
                )
            parsed_ids = list(
                dict.fromkeys(pattern_id for pattern_id in parsed_ids_raw if pattern_id != name)
            )

            if parsed_ids:
                n_ids = len(parsed_ids)
                cap = _max_var_repeat()
                if cap and n_ids > cap:
                    raise RuntimeError(
                        f"PARSER: variable {name!r} expands to {n_ids} instances, exceeding "
                        f"the cap of {cap}. Raise RING5_MAX_VAR_REPEAT, or set it to 0 for "
                        "trusted inputs, to include it."
                    )

            duplicate_alias = next((pid for pid in parsed_ids if pid in var_map), None)
            if duplicate_alias is not None:
                raise RuntimeError(
                    f"PARSER: Duplicate variable or alias definition: {duplicate_alias}"
                )
            projected_variables = len(var_map) + 1 + len(parsed_ids)
            if projected_variables > MAX_PARSE_VARIABLES:
                raise RuntimeError(
                    f"PARSER: {projected_variables} logical variables and aliases exceed the "
                    f"{MAX_PARSE_VARIABLES}-variable limit."
                )

            if parsed_ids:
                # Resolve repeat count for the logical variable (spatial aggregation).
                source_pattern = var.source_name or name
                entry_ids: list[str] = []
                try:
                    entry_ids = [
                        pattern_id
                        for parsed_id in parsed_ids
                        if (pattern_id := numeric_pattern_id(source_pattern, parsed_id)) is not None
                    ]
                except SafeRegexError:
                    entry_ids = []
                configured_entries = var.params.get("entries", [])
                # Repeated scalar names are exposed by the scanner as a logical
                # vector whose entries are the numeric IDs.  Each entry contains
                # one value, so padding it to ``n_ids`` makes every mean NaN.
                # True vector/distribution patterns still aggregate the same
                # bucket across all concrete instances and retain repeat=n_ids.
                scalar_pattern_vector = (
                    var.type == "vector"
                    and isinstance(configured_entries, list)
                    and set(entry_ids) == set(configured_entries)
                    and len(entry_ids) == n_ids
                )
                repeat = var.repeat if scalar_pattern_vector else n_ids
                stat_obj = TypeMapper.create_stat(replace(var, repeat=repeat))
                if n_ids > 50:
                    logger.warning(
                        "PARSER: Variable '%s' expands to %d concrete instances — "
                        "this may increase memory usage significantly.",
                        name,
                        n_ids,
                    )
            else:
                stat_obj = TypeMapper.create_stat(var)

            var_map[name] = stat_obj

            # Aliases share content within a template; work items deep-copy the
            # template to isolate files.
            for pid in parsed_ids:
                if pid != name:
                    var_map[pid] = copy.copy(stat_obj)

        return var_map
