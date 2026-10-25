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
    UnicodeDecodeError,
)


def classify_parse_failure(
    error: BaseException,
) -> Literal["data", "io", "configuration", "transport", "encoding"] | None:
    """Identify exact known producer errors before any wrapping or retry policy.

    Configuration errors are wrapped by their input owner; only data and builtin
    IO errors are directly detachable. Unsupported subclasses remain unexpected.
    """
    error_type = type(error)
    if error_type in _DATA_ERRORS:
        return "data"
    if error_type in _IO_ERRORS:
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
        for code in (error.errno, getattr(error, "winerror", None)):
            if code is not None and (type(code) is not int or code.bit_length() > 32):
                return None
        return "io"
    if error_type in _CONFIGURATION_ERRORS:
        return "configuration"
    if error_type is queue.Empty:
        return "transport"
    if error_type is UnicodeEncodeError:
        return "encoding"
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
    if type(error) in (UnicodeEncodeError, UnicodeDecodeError):
        assert isinstance(error, (UnicodeEncodeError, UnicodeDecodeError))
        return bounded_parse_text(
            f"{error.encoding} positions {error.start}:{error.end}: {error.reason}"
        )
    fragments: list[str] = []
    for argument in islice(error.args, 8):
        if type(argument) is str:
            fragments.append(bounded_parse_text(argument))
        elif type(argument) is int and argument.bit_length() > 64:
            fragments.append("<int>")
        elif type(argument) in (int, float, bool) or argument is None:
            fragments.append(str(argument))
        else:
            fragments.append(f"<{type(argument).__name__}>")
    return bounded_parse_text("; ".join(fragments))


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
        # Builtin IO constructors preserve errno and both filenames. Windows
        # accepts winerror in the fourth position; other platforms ignore None.
        filename = error.filename
        filename2 = error.filename2
        strerror = bounded_parse_text(error.strerror) if type(error.strerror) is str else message
        if type(error.errno) is int:
            winerror = getattr(error, "winerror", None)
            fresh = error_type(error.errno, strerror, filename, winerror, filename2)
        else:
            fresh = error_type(message)

    locations: deque[str] = deque(maxlen=8)
    node = error.__traceback__
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
    cause = error.__cause__ or error.__context__
    while cause is not None and id(cause) not in seen and len(causes) < 8:
        seen.add(id(cause))
        causes.append(f"{type(cause).__name__}: {parse_error_text(cause)}")
        cause = cause.__cause__ or cause.__context__
    fresh.__dict__["failure_facts"] = ParseFailureFacts(
        source_path,
        bounded_parse_text(" <- ".join(locations), MAX_PARSE_FAILURE_ORIGIN),
        bounded_parse_text(" <- ".join(causes), MAX_PARSE_FAILURE_CAUSE),
    )
    return fresh
