"""Parse one gem5 statistics file through exact concrete-source bindings."""

from __future__ import annotations

import logging
import re

from src.parsing.gem5.types.base import StatContent, StatResult, StatType

from src.core.common.parsed_output_codec import read_numeric_wire
from src.core.common.source_entry_labels import canonical_source_entry
from src.core.models.source_evidence import SourceKindBinding
from src.core.models.native_distribution_layout import NativeDistributionLayout
from src.parsing.gem5.impl.source_bindings import AccumulatorSpec
from src.parsing.gem5.impl.source_events import (
    Measurement,
    SourceEvidence,
    SourceFailure,
    DumpBoundary,
    decode_source_event,
)
from src.core.common.parse_failure import (
    bounded_parse_text,
    classify_parse_failure,
    parse_error_text,
    parse_names_text,
)
from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError
from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_VARIABLES,
    MAX_PARSED_CELL_CHARACTERS,
)
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
EntryBufferType = dict[tuple[str, str], list[dict[str, str]]]
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
        self._source_buffer: dict[str, list[Measurement]] = {}
        self._entry_ordinals: dict[tuple[str, str, str], int] = {}

    def __str__(self) -> str:
        return f"Gem5ParseWork({self._file_to_parse})"

    @property
    def source_path(self) -> str:
        """Return the exact statistics file parsed by this worker."""
        return self._file_to_parse

    def _buffer_entry(
        self,
        output_name: str,
        source_name: str,
        entry_name: str,
        value: str,
        *,
        sample_index: int | None = None,
    ) -> None:
        key = (output_name, source_name, entry_name)
        index = self._entry_ordinals.get(key, 0) if sample_index is None else sample_index
        frames = self._entry_buffer.setdefault((output_name, source_name), [])
        while len(frames) <= index:
            frames.append({})
        if entry_name in frames[index]:
            raise ParseDataValueError("A source observation repeats the same native cell position.")
        frames[index][entry_name] = value
        self._entry_ordinals[key] = max(index + 1, self._entry_ordinals.get(key, 0))

    def _apply_buffered_entries(self) -> None:
        """Commit actual source frames without allocating requested-repeat padding."""
        scalar_vectors: dict[str, list[dict[str, float]]] = {}
        for (output_name, _source_name), raw_frames in self._entry_buffer.items():
            accumulator = self._accumulators[output_name]
            spec = self._specs[output_name]
            for index, raw_sample in enumerate(raw_frames):
                sample = {entry: read_numeric_wire(value) for entry, value in raw_sample.items()}
                if spec.output_type == "vector" and spec.config.params["source_type"] == "scalar":
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
        self._entry_ordinals = {}

    @staticmethod
    def _matches_native_header(value: float, token: str) -> bool:
        """Compare the exact declared double at the printed fixed decimal precision."""
        if (
            len(token) > MAX_PARSED_CELL_CHARACTERS
            or re.fullmatch(r"-?\d+(?:\.\d+)?", token) is None
        ):
            return False
        places = len(token.partition(".")[2])
        return format(value, f".{places}f") == token

    def _oneline_entries(
        self,
        measurement: Measurement,
        source_kind: str,
        spec: AccumulatorSpec,
    ) -> list[tuple[str, str]]:
        """Admit each selected representation against its own declared source grid."""
        if spec.config.statistics_only:
            return []
        reported = dict(measurement.reported_geometry)
        layout = spec.layout
        if source_kind == "distribution" and type(layout) is NativeDistributionLayout:
            geometry = layout.geometry
            expected = {
                "bucket_size": geometry.bucket_size,
                "min_bucket": geometry.minimum,
                "max_bucket": geometry.maximum,
            }
            if "bucket_size" not in reported or any(
                key not in reported and not (layout.zero_policy == "nozero" and value == 0.0)
                for key, value in expected.items()
            ):
                raise ParseDataValueError(
                    "Oneline Distribution requires its reported width and declared bounds."
                )
            if any(
                not self._matches_native_header(expected[key], value)
                for key, value in reported.items()
            ):
                raise ParseDataValueError("Printed geometry contradicts the declared native grid.")
            labels = [column.source_label for column in layout.columns if column.role == "bucket"]
        elif source_kind in {"histogram", "distribution"} and (
            source_kind == "histogram" or spec.output_type == "histogram"
        ):
            if set(reported) != {"bucket_size", "min_bucket", "max_bucket"} or any(
                re.fullmatch(r"-?\d+", value) is None for value in reported.values()
            ):
                raise ParseDataValueError(
                    "Generic Histogram requires complete integral geometry; use a declared "
                    "native Distribution grid for fractional storage cells."
                )
            integral: dict[str, int] = {}
            for key, value in reported.items():
                read_numeric_wire(value)
                try:
                    integral[key] = int(value)
                except ValueError as exc:
                    if type(exc) is not ValueError:
                        raise
                    raise ParseDataValueError(
                        "Integral source geometry exceeds its bound."
                    ) from exc
            width, low, high = (
                integral[key] for key in ("bucket_size", "min_bucket", "max_bucket")
            )
            if width <= 0 or high < low:
                raise ParseDataValueError(
                    "Invalid oneline Histogram geometry; use a declared native Distribution "
                    "grid for native storage cells."
                )
            count = (high - low) // width + 1
            if count > MAX_INCREMENTAL_CACHE_COLUMNS:
                raise ParseDataValueError("Oneline Histogram exceeds the physical column limit.")
            labels = [
                f"{low + index * width}-{min(low + (index + 1) * width - 1, high)}"
                for index in range(count)
            ]
        else:
            raise ParseDataValueError(
                "Oneline Vector has no entry-order contract; select native Distribution "
                "output with an explicit full grid."
            )
        if len(labels) != len(measurement.values):
            raise ParseDataValueError("Oneline source cell count contradicts its current geometry.")
        return list(zip(labels, measurement.values, strict=True))

    def _consume_source(self, source: SourceEvidence) -> None:
        """Check actual shared evidence before an observation reaches an accumulator."""
        route = self._routes.get(source.name)
        if route is None:
            raise ParseDataValueError("Decoder returned an unplanned source.")
        source_kind = self._specs[route.targets[0].output_name].config.params["source_type"]
        if type(source_kind) is not str:
            raise RuntimeError("The immutable source plan lost its request declaration.")
        try:
            SourceKindBinding(source_kind, source.evidence)
        except ValueError as exc:
            if type(exc) is not ValueError:
                raise
            raise ParseDataRuntimeError(
                f"Declared source contract contradicts actual observations for {source.name!r}."
            ) from exc
        measurements = self._source_buffer.pop(source.name, [])
        native_headers = source_kind == "distribution" and any(
            item.shape == "entry" and item.entry == "samples" for item in measurements
        )
        frame_index = 0
        samples_seen = 0
        oneline_index = 0
        for measurement in measurements:
            if native_headers and measurement.shape == "entry" and measurement.entry == "samples":
                frame_index = samples_seen
                samples_seen += 1
            sample_index = frame_index if native_headers else None
            if measurement.shape == "oneline":
                if not native_headers:
                    sample_index = oneline_index
                oneline_index += 1
                for target in route.targets:
                    spec = self._specs[target.output_name]
                    for entry, value in self._oneline_entries(measurement, source_kind, spec):
                        self._buffer_entry(
                            target.output_name, source.name, entry, value, sample_index=sample_index
                        )
                continue
            if measurement.shape == "entry":
                assert measurement.entry is not None and measurement.value is not None
                entry = measurement.entry
                if source_kind in {"histogram", "distribution"} and entry in {
                    "bucket_size",
                    "min_bucket",
                    "max_bucket",
                }:
                    continue
                entry = canonical_source_entry(source_kind, entry)
                for target in route.targets:
                    spec = self._specs[target.output_name]
                    if spec.output_type not in _ENTRY_TYPES or target.entry_name is not None:
                        raise RuntimeError("Entry source has an incompatible planned destination.")
                    if (
                        source_kind == "distribution"
                        and spec.output_type == "histogram"
                        and (
                            re.fullmatch(r"-?\d+(?:--?\d+)?", entry) is None
                            and any(character.isdigit() for character in entry)
                        )
                    ):
                        raise ParseDataValueError(
                            "Generic Histogram cannot interpret fractional native cells; use "
                            "Distribution output with an explicit full grid."
                        )
                    self._buffer_entry(
                        target.output_name,
                        source.name,
                        entry,
                        measurement.value,
                        sample_index=sample_index,
                    )
                continue
            assert measurement.value is not None
            for target in route.targets:
                spec = self._specs[target.output_name]
                if (
                    spec.output_type == "vector"
                    and source_kind == "scalar"
                    and target.entry_name is not None
                ):
                    self._buffer_entry(
                        target.output_name, source.name, target.entry_name, measurement.value
                    )
                elif spec.output_type in {"scalar", "configuration"} and target.entry_name is None:
                    self._accumulators[target.output_name].add_observation(
                        measurement.value
                        if spec.output_type == "configuration"
                        else read_numeric_wire(measurement.value)
                    )
                else:
                    raise RuntimeError("Point source has an incompatible planned destination.")

    def _process_line(self, line: str) -> None:
        event = decode_source_event(line)
        if isinstance(event, Measurement):
            if event.name not in self._routes:
                raise ParseDataValueError("Decoder returned an unplanned measurement.")
            self._source_buffer.setdefault(event.name, []).append(event)
        elif isinstance(event, SourceEvidence):
            self._consume_source(event)
        elif isinstance(event, SourceFailure):
            raise ParseDataRuntimeError(f"Source {event.name!r}: {event.message}")
        elif isinstance(event, DumpBoundary):
            if self._source_buffer:
                raise ParseDataValueError("Decoder omitted completed source evidence.")
            self._apply_buffered_entries()

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
        self._entry_ordinals = {}
        self._source_buffer = {}
        for line in output.splitlines():
            if line.strip():
                self._process_line(line)
        if self._source_buffer:
            raise ParseDataValueError("Decoder omitted final source evidence.")
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
            variables.append(
                ParsedVariableResult(name, kind, shape, cells, missing, layout=spec.layout)
            )
        return ParsedFileResult(self._file_to_parse, tuple(variables))
