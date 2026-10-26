"""Parse one gem5 statistics file through exact concrete-source bindings."""

from __future__ import annotations

import logging
import re

from src.parsing.gem5.types.base import StatContent, StatResult, StatType

from src.core.common.parsed_output_codec import read_numeric_wire
from src.core.common.parse_failure import (
    bounded_parse_text,
    classify_parse_failure,
    parse_error_text,
    parse_names_text,
)
from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError
from src.core.common.security_limits import MAX_INCREMENTAL_CACHE_COLUMNS, MAX_PARSE_VARIABLES
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedFileResult,
    ParsedKind,
    ParsedShape,
    ParsedVariableResult,
)
from src.core.common.utils import checkFileExistsOrException
from src.parsing.gem5.impl.source_bindings import SourcePlan, literal_source_filter
from src.parsing.gem5.impl.strategies.perl_worker_pool import get_worker_pool

VarsDictType = dict[str, StatType[StatContent, StatResult]]
EntryBufferType = dict[tuple[str, str], dict[str, list[str]]]
_ENTRY_TYPES = frozenset({"vector", "distribution", "histogram"})
logger = logging.getLogger(__name__)


class Gem5ParseWork:
    """Own per-file accumulators while sharing immutable source routing metadata."""

    def __init__(self, file_to_parse: str, accumulators: VarsDictType, plan: SourcePlan) -> None:
        """Create a worker from one resolved parse plan.

        Args:
            file_to_parse: Exact statistics file owned by this worker.
            accumulators: Independent mutable accumulator for each logical output.
            plan: Resolved configurations and immutable concrete-source routes.

        Raises:
            ValueError: Accumulator names do not match the plan.
            RuntimeError: No source/accumulator work was provided or a limit is exceeded.
        """
        if not accumulators or not plan.routes:
            raise RuntimeError("A parse worker requires logical accumulators and concrete sources.")
        if set(accumulators) != {spec.output_name for spec in plan.accumulators}:
            raise ValueError("Worker accumulators must exactly match the resolved output names.")
        if len(plan.routes) > MAX_PARSE_VARIABLES:
            raise RuntimeError("Parser source filters exceed the variable limit.")
        self._file_to_parse = file_to_parse
        self._accumulators = accumulators
        self._routes = plan.routes
        self._specs = {spec.output_name: spec for spec in plan.accumulators}
        self._entry_buffer: EntryBufferType = {}

    def __str__(self) -> str:
        return f"Gem5ParseWork({self._file_to_parse})"

    @property
    def source_path(self) -> str:
        """Return the exact statistics file parsed by this worker."""
        return self._file_to_parse

    def _buffer_entry(
        self, output_name: str, source_name: str, entry_name: str, value: str
    ) -> None:
        entries = self._entry_buffer.setdefault((output_name, source_name), {})
        entries.setdefault(entry_name, []).append(value)

    def _apply_buffered_entries(self) -> None:
        """Apply each source's temporal samples independently to its logical target."""
        scalar_vectors: dict[str, list[dict[str, float]]] = {}
        for (output_name, _source_name), entries in self._entry_buffer.items():
            accumulator = self._accumulators[output_name]
            spec = self._specs[output_name]
            for index in range(max(map(len, entries.values()), default=0)):
                sample = {
                    entry: read_numeric_wire(values[index])
                    for entry, values in entries.items()
                    if index < len(values)
                }
                if spec.output_type == "vector" and spec.config.params["source_type"] == "scalar":
                    # Independent scalar sources populate distinct entries of one
                    # temporal vector frame rather than separate observations.
                    frames = scalar_vectors.setdefault(output_name, [])
                    while len(frames) <= index:
                        frames.append({})
                    frames[index].update(sample)
                else:
                    accumulator.add_observation(sample)
        for output_name, frames in scalar_vectors.items():
            for sample in frames:
                self._accumulators[output_name].add_observation(sample)
        self._entry_buffer = {}

    @staticmethod
    def _parse_line(line: str) -> tuple[str, str, str] | None:
        parts = line.split("/", 2)
        if len(parts) != 3:
            logger.warning("PARSER: Malformed worker output line: %s", line[:200])
            return None
        return parts[0], parts[1], parts[2]

    def _process_line(self, line: str) -> None:
        parsed = self._parse_line(line)
        if parsed is None:
            return
        raw_type, identifier, value = parsed
        source_name, separator, raw_entry = identifier.partition("::")
        route = self._routes.get(source_name)
        if route is None:
            return

        if separator:
            if route.source_type not in _ENTRY_TYPES or (
                raw_type != "summary" and raw_type != route.source_type
            ):
                raise ParseDataRuntimeError(
                    f"Raw source kind mismatch for {source_name!r}: {raw_type!r}."
                )
            for target in route.targets:
                spec = self._specs[target.output_name]
                if spec.output_type not in _ENTRY_TYPES or target.entry_name is not None:
                    raise RuntimeError(
                        f"Entry source cannot populate output {target.output_name!r}."
                    )
                entry = raw_entry
                if route.source_type == "histogram" and spec.output_type == "vector":
                    if re.fullmatch(r"-?\d+", entry):
                        entry = f"{entry}-{entry}"
                self._buffer_entry(target.output_name, source_name, entry, value)
            return

        if raw_type not in {"scalar", "configuration"} or raw_type != route.source_type:
            raise ParseDataRuntimeError(
                f"Raw source kind mismatch for {source_name!r}: {raw_type!r}."
            )
        for target in route.targets:
            spec = self._specs[target.output_name]
            if (
                spec.output_type == "vector"
                and raw_type == "scalar"
                and target.entry_name is not None
            ):
                self._buffer_entry(target.output_name, source_name, target.entry_name, value)
            elif spec.output_type in {"scalar", "configuration"} and target.entry_name is None:
                self._accumulators[target.output_name].add_observation(
                    value if spec.output_type == "configuration" else read_numeric_wire(value)
                )
            else:
                raise RuntimeError(f"Scalar source cannot populate output {target.output_name!r}.")

    def _validate_variables(self) -> VarsDictType:
        """Keep missing numeric observations visible and honor explicit configuration fallbacks."""
        # [impl->req~ring5.ingestion.configuration-fallbacks~1]
        missing: list[str] = []
        for name, accumulator in self._accumulators.items():
            spec = self._specs[name]
            if spec.output_type == "configuration":
                # The typed text accumulator owns its explicit empty-input policy.
                continue
            if accumulator.missing_measurement_count:
                missing.append(name)
        if missing:
            logger.warning(
                "PARSER: %d requested output(s) absent or incomplete in %s — recorded as NaN: %s",
                len(missing),
                self._file_to_parse,
                parse_names_text(sorted(missing)),
            )
        return self._accumulators

    def _process_output(self, output: str) -> VarsDictType:
        self._entry_buffer = {}
        for line in output.splitlines():
            if not line.strip():
                continue
            if line == "dump//":
                self._apply_buffered_entries()
            else:
                self._process_line(line)
        self._apply_buffered_entries()
        return self._validate_variables()

    def _run_perl_script(self) -> str:
        checkFileExistsOrException(self._file_to_parse)
        filters = [literal_source_filter(source_name) for source_name in self._routes]
        logger.debug("Parsing %s with %d concrete sources", self._file_to_parse, len(filters))
        try:
            lines = get_worker_pool().parse_file(self._file_to_parse, filters, timeout=120.0)
            return "\n".join(lines)
        except TimeoutError as exc:
            if classify_parse_failure(exc) is None:
                raise
            raise ParseDataRuntimeError(f"Parser timeout: {self._file_to_parse}") from exc
        except (OSError, ParseDataRuntimeError, ParseDataValueError) as exc:
            if classify_parse_failure(exc) is None:
                raise
            message = bounded_parse_text(
                f"Worker pool parse failed for {self._file_to_parse}: {parse_error_text(exc)}"
            )
            logger.error("%s", message)
            raise ParseDataRuntimeError(message) from exc

    def __call__(self) -> ParsedFileResult:
        """Parse, balance and reduce owned accumulators before resolving this worker."""
        accumulators = self._process_output(self._run_perl_script())
        variables: list[ParsedVariableResult] = []
        column_count = 0
        for name, accumulator in accumulators.items():
            spec = self._specs[name]
            missing = accumulator.missing_measurement_count
            accumulator.balance_content()
            accumulator.reduce_duplicates()
            reduced = accumulator.reduced_content
            kind: ParsedKind
            shape: ParsedShape
            cells: tuple[ParsedCell, ...]
            if spec.output_type in {"configuration", "scalar"}:
                if isinstance(reduced, dict):
                    raise RuntimeError(
                        f"PARSER: scalar output {name!r} requires one reduced value."
                    )
                kind = "text" if spec.output_type == "configuration" else "number"
                cells = (ParsedCell(name, kind, reduced),)
                shape = "scalar"
            elif spec.output_type in _ENTRY_TYPES:
                entries = accumulator.entries
                if type(reduced) is not dict or entries is None:
                    raise RuntimeError(
                        f"PARSER: entry output {name!r} requires reduced entry values."
                    )
                if column_count + len(entries) > MAX_INCREMENTAL_CACHE_COLUMNS:
                    raise ParseDataRuntimeError("PARSER: output exceeds the physical column limit.")
                cells = tuple(
                    ParsedCell(f"{name}..{entry}", "number", reduced[entry]) for entry in entries
                )
                kind, shape = "number", "entries"
            else:
                raise ValueError(f"PARSER: unsupported output representation {spec.output_type!r}.")
            column_count += len(cells)
            if column_count > MAX_INCREMENTAL_CACHE_COLUMNS:
                raise ParseDataRuntimeError("PARSER: output exceeds the physical column limit.")
            variables.append(ParsedVariableResult(name, kind, shape, cells, missing))
        return ParsedFileResult(self._file_to_parse, tuple(variables))
