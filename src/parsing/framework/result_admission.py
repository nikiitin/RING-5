"""Per-submission admission of finalized values before Futures retain them."""

from __future__ import annotations

import threading

from src.core.common.parsed_output_codec import iter_parsed_file_encoding
from src.core.common.parse_failure import (
    classify_parse_failure,
    detach_parse_failure,
    parse_error_text,
)
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import (
    MAX_PARSE_FILES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_RESULT_BYTES,
)
from src.core.models.parsed_output_models import ParsedFileResult
from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataTypeError,
    ParseDataValueError,
    ResultAdmissionError,
)
from src.parsing.parser_protocol import ParseWorkItem


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

    def require_source_path(self, value: object) -> str:
        """Require an exact bounded source ID from this admission's immutable plan."""
        if type(value) is not str or len(value) > MAX_INPUT_LENGTH or value not in self._planned:
            raise ResultAdmissionError("PARSER: work source must be an exact planned source ID.")
        return value

    def admit(self, result: ParsedFileResult, *, source_path: str) -> None:
        """Admit one exact source association atomically before retaining its result."""
        source_path = self.require_source_path(source_path)
        if type(result) is not ParsedFileResult:
            raise ResultAdmissionError(
                f"PARSER: worker {source_path!r} must return typed ParsedFileResult values."
            )
        if result.source_path != source_path:
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
            except (ParseDataValueError, ParseDataTypeError, UnicodeEncodeError) as exc:
                if classify_parse_failure(exc) not in ("data", "encoding"):
                    raise
                raise ResultAdmissionError(
                    f"PARSER: invalid typed result record: {parse_error_text(exc)}"
                ) from exc
            self._cells += cells
            self._bytes += size
            self._admitted.add(source_path)


class AdmittedParseWork:
    """Consume one typed work item and publish only an admitted immutable value."""

    def __init__(self, work: ParseWorkItem, admission: ResultAdmission) -> None:
        self._source_path = admission.require_source_path(work.source_path)
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
        expected_failure: BaseException | None = None
        result: ParsedFileResult | None = None
        try:
            result = work()
            self._admission.admit(result, source_path=self._source_path)
        except (
            ParseDataRuntimeError,
            ParseDataTypeError,
            ParseDataValueError,
            ResultAdmissionError,
            OSError,
        ) as exc:
            expected_failure = detach_parse_failure(exc, self._source_path)
            if expected_failure is None:
                raise
        finally:
            del work
        if expected_failure is not None:
            # Leaving the handler also removes implicit exception context. The
            # fresh traceback owns this consumed wrapper, never producer frames.
            del result
            raise expected_failure
        assert result is not None
        return result
