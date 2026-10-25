"""Per-submission admission of finalized values before Futures retain them."""

from __future__ import annotations

import threading

from src.core.common.parsed_output_codec import iter_parsed_file_encoding
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import (
    MAX_PARSE_FILES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_RESULT_BYTES,
)
from src.core.models.parsed_output_models import ParsedFileResult
from src.parsing.parser_protocol import ParseWorkItem


class ResultAdmissionError(ValueError):
    """A finalized file exceeds its source-owned batch's retained-result limits."""


class ResultAdmission:
    """Monotonically charge accepted file records without retaining their values.

    The byte quota counts the canonical UTF-8 typed record, including repeated
    per-file names, declarations, values and metadata. It is independent of the
    final CSV byte quota and rectangular matrix check. Failed admission commits
    no counters; cancellation never recycles already accepted quota.
    """

    def __init__(self, source_paths: tuple[str, ...]) -> None:
        if (
            type(source_paths) is not tuple
            or not source_paths
            or len(source_paths) > MAX_PARSE_FILES
        ):
            raise ValueError("Result admission requires the bounded immutable source plan.")
        if any(
            type(path) is not str or not path or len(path) > MAX_INPUT_LENGTH
            for path in source_paths
        ):
            raise ValueError("Result admission source IDs must be bounded non-empty strings.")
        if len(set(source_paths)) != len(source_paths):
            raise ValueError("Result admission source IDs must be unique.")
        self._planned = frozenset(source_paths)
        self._admitted: set[str] = set()
        self._cells = 0
        self._bytes = 0
        self._lock = threading.Lock()

    def admit(self, result: ParsedFileResult, *, source_path: str) -> None:
        """Admit one exact source association atomically before retaining its result."""
        if type(result) is not ParsedFileResult:
            raise ResultAdmissionError(
                f"PARSER: worker {source_path!r} must return typed ParsedFileResult values."
            )
        if result.source_path != source_path or source_path not in self._planned:
            raise ResultAdmissionError(
                f"PARSER: worker result does not match its planned source {source_path!r}."
            )
        cells = len(result.metadata) + sum(len(variable.cells) for variable in result.variables)
        with self._lock:
            if source_path in self._admitted:
                raise ResultAdmissionError(
                    f"PARSER: duplicate result admission for {source_path!r}."
                )
            if self._cells + cells > MAX_PARSE_MATRIX_CELLS:
                raise ResultAdmissionError(
                    "PARSER: batch results exceed the "
                    f"{MAX_PARSE_MATRIX_CELLS}-cell admission limit for {source_path!r}."
                )
            size = 0
            try:
                for fragment in iter_parsed_file_encoding(result):
                    size += len(fragment)
                    if self._bytes + size > MAX_PARSE_RESULT_BYTES:
                        raise ResultAdmissionError(
                            "PARSER: batch results exceed the "
                            f"{MAX_PARSE_RESULT_BYTES}-byte retained-record admission limit "
                            f"for {source_path!r}."
                        )
            except ResultAdmissionError:
                raise
            except (TypeError, ValueError) as exc:
                raise ResultAdmissionError(f"PARSER: invalid typed result record: {exc}") from exc
            self._cells += cells
            self._bytes += size
            self._admitted.add(source_path)


class AdmittedParseWork:
    """Consume one typed work item and publish only an admitted immutable value."""

    def __init__(self, work: ParseWorkItem, admission: ResultAdmission) -> None:
        self._source_path = work.source_path
        self._work: ParseWorkItem | None = work
        self._admission = admission

    @property
    def source_path(self) -> str:
        """Return the fixed source association captured before submission."""
        return self._source_path

    def __call__(self) -> ParsedFileResult:
        """Return admitted values without rejected data in admission-error tracebacks."""
        work, self._work = self._work, None
        if work is None:
            raise RuntimeError("A parse work item can execute only once.")
        try:
            result = work()
        finally:
            del work
        failure: str | None = None
        try:
            self._admission.admit(result, source_path=self._source_path)
        except ResultAdmissionError as exc:
            failure = str(exc)
        if failure is not None:
            # Raising after the handler avoids retaining the original traceback,
            # which owns the rejected value and its temporary encoding graph.
            del result
            raise ResultAdmissionError(failure)
        return result
