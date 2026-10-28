"""Detach known parser data failures without retaining producer tracebacks."""

from __future__ import annotations

import configparser
import queue
from collections import deque
from collections.abc import Iterable
from itertools import islice
from typing import Literal

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataTypeError,
    ParseDataValueError,
    ParseFailureFacts,
    ResultAdmissionError,
)

MAX_PARSE_FAILURE_MESSAGE = 1024
MAX_PARSE_FAILURE_ORIGIN = 2048
MAX_PARSE_FAILURE_CAUSE = 1024
_TRUNCATED = " ... [truncated]"
_DATA_ERRORS = (
    ParseDataRuntimeError,
    ParseDataTypeError,
    ParseDataValueError,
    ResultAdmissionError,
)
_IO_ERRORS = (
    OSError,
    FileNotFoundError,
    FileExistsError,
    IsADirectoryError,
    NotADirectoryError,
    PermissionError,
    BrokenPipeError,
    ConnectionResetError,
    InterruptedError,
    TimeoutError,
)
_CONFIGURATION_ERRORS = (
    configparser.Error,
    configparser.ParsingError,
    configparser.MissingSectionHeaderError,
    configparser.DuplicateOptionError,
    configparser.DuplicateSectionError,
)


def _type_label(value: object) -> str:
    name = type.__dict__["__name__"].__get__(type(value))
    return bounded_parse_text(name, 80) if type(name) is str else "object"


def _unicode_metadata(error: BaseException) -> tuple[object, object, object, object] | None:
    for owner in type.__dict__["__mro__"].__get__(type(error)):
        if owner is UnicodeEncodeError or owner is UnicodeDecodeError:
            return (
                owner.__dict__["encoding"].__get__(error),
                owner.__dict__["reason"].__get__(error),
                owner.__dict__["start"].__get__(error),
                owner.__dict__["end"].__get__(error),
            )
    return None


def _native_unicode_metadata(metadata: tuple[object, object, object, object]) -> bool:
    encoding, reason, start, end = metadata
    return (
        type(encoding) is str
        and type(reason) is str
        and type(start) is int
        and type(end) is int
        and start.bit_length() <= 63
        and end.bit_length() <= 63
        and 0 <= start <= end
    )


def _argument_text(value: object) -> str:
    if type(value) is str:
        return bounded_parse_text(value)
    if type(value) is int and value.bit_length() > 63:
        return "<int>"
    if type(value) is int or type(value) is float or type(value) is bool or value is None:
        return str(value)
    return f"<{_type_label(value)}>"


def _next_cause(error: BaseException) -> BaseException | None:
    cause: BaseException | None = BaseException.__dict__["__cause__"].__get__(error)
    context: BaseException | None = BaseException.__dict__["__context__"].__get__(error)
    return cause if cause is not None else context


def classify_parse_failure(
    error: BaseException,
) -> Literal["data", "io", "configuration", "transport", "encoding"] | None:
    """Identify exact known producer errors before any wrapping or retry policy.

    Configuration errors are wrapped by their input owner; only data and builtin
    IO errors are directly detachable. Unsupported subclasses remain unexpected.
    """
    error_type = type(error)
    if any(error_type is known for known in _DATA_ERRORS):
        return "data"
    if any(error_type is known for known in _IO_ERRORS):
        assert isinstance(error, OSError)
        # Owned parser paths are bounded text. Decline mutated/non-native IO
        # metadata before any inner owner can wrap it or invoke a constructor.
        for filename in (error.filename, error.filename2):
            if filename is not None and (
                type(filename) is not str or len(filename) > MAX_INPUT_LENGTH
            ):
                return None
        if error.strerror is not None and type(error.strerror) is not str:
            return None
        code = error.errno
        if code is not None and (type(code) is not int or code.bit_length() > 32):
            return None
        return "io"
    if any(error_type is known for known in _CONFIGURATION_ERRORS):
        return "configuration"
    if error_type is queue.Empty:
        return "transport"
    if error_type is UnicodeEncodeError or error_type is UnicodeDecodeError:
        metadata = _unicode_metadata(error)
        if metadata is None or not _native_unicode_metadata(metadata):
            return None
        return "encoding" if error_type is UnicodeEncodeError else "configuration"
    return None


def bounded_parse_text(value: str, limit: int = MAX_PARSE_FAILURE_MESSAGE) -> str:
    """Bound already-rendered diagnostic text, including the truncation marker."""
    return value if len(value) <= limit else value[: limit - len(_TRUNCATED)] + _TRUNCATED


def parse_error_text(error: BaseException) -> str:
    """Render bounded primitive arguments without invoking arbitrary value hooks.

    Known parser data errors have text arguments. Configuration parser errors
    also hold their diagnostic text in their arguments; their raw source buffers,
    error lists and Unicode decoder objects are deliberately excluded.
    """
    metadata = _unicode_metadata(error)
    if metadata is not None:
        encoding, reason, start, end = (_argument_text(value) for value in metadata)
        return bounded_parse_text(f"{encoding} positions {start}:{end}: {reason}")
    arguments = BaseException.__dict__["args"].__get__(error)
    if type(arguments) is not tuple:
        return "<non-native exception arguments>"
    return bounded_parse_text("; ".join(_argument_text(value) for value in islice(arguments, 8)))


def parse_names_text(values: Iterable[str]) -> str:
    """Render a bounded diagnostic sample without retaining its source container."""
    parts: list[str] = []
    for value in islice(values, 8):
        parts.append(repr(bounded_parse_text(value, 120)))
    return bounded_parse_text(", ".join(parts))


def detach_parse_failure(error: BaseException, source_path: str) -> BaseException | None:
    """Copy only recognized errors into bounded text and immutable IO facts.

    Returns ``None`` for unmarked programming exceptions, including subclasses
    of the reviewed builtin IO classes. No exception cloning or plugin hooks run.
    The caller raises the returned error after leaving its original handler.
    """
    error_type = type(error)
    classification = classify_parse_failure(error)
    if classification not in ("data", "io"):
        return None
    message = parse_error_text(error)
    fresh: BaseException
    if classification == "data":
        fresh = error_type(message)
    else:
        assert isinstance(error, OSError)
        # The fifth constructor position preserves the second filename.
        filename = error.filename
        filename2 = error.filename2
        strerror = bounded_parse_text(error.strerror) if type(error.strerror) is str else message
        if type(error.errno) is int:
            fresh = error_type(error.errno, strerror, filename, None, filename2)
        else:
            fresh = error_type(message)

    locations: deque[str] = deque(maxlen=8)
    node = BaseException.__dict__["__traceback__"].__get__(error)
    while node is not None:
        frame = node.tb_frame
        module = frame.f_globals.get("__name__")
        module = module if type(module) is str else "<unknown>"
        locations.append(
            bounded_parse_text(f"{module}.{frame.f_code.co_name}:{node.tb_lineno}", 256)
        )
        node = node.tb_next
    causes: list[str] = []
    seen = {id(error)}
    cause = _next_cause(error)
    while cause is not None and id(cause) not in seen and len(causes) < 8:
        seen.add(id(cause))
        causes.append(f"{_type_label(cause)}: {parse_error_text(cause)}")
        cause = _next_cause(cause)
    fresh.__dict__["failure_facts"] = ParseFailureFacts(
        source_path,
        bounded_parse_text(" <- ".join(locations), MAX_PARSE_FAILURE_ORIGIN),
        bounded_parse_text(" <- ".join(causes), MAX_PARSE_FAILURE_CAUSE),
    )
    return fresh
