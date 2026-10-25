"""Detach known parser data failures without retaining producer tracebacks."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from itertools import islice

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataTypeError,
    ParseDataValueError,
    ParseFailureFacts,
)

MAX_PARSE_FAILURE_MESSAGE = 1024
MAX_PARSE_FAILURE_ORIGIN = 2048
MAX_PARSE_FAILURE_CAUSE = 1024
_TRUNCATED = " ... [truncated]"
_DATA_ERRORS = (ParseDataRuntimeError, ParseDataTypeError, ParseDataValueError)
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


def bounded_parse_text(value: str, limit: int = MAX_PARSE_FAILURE_MESSAGE) -> str:
    """Bound already-rendered diagnostic text, including the truncation marker."""
    return value if len(value) <= limit else value[: limit - len(_TRUNCATED)] + _TRUNCATED


def parse_error_text(error: BaseException) -> str:
    """Render bounded primitive arguments without invoking arbitrary value hooks.

    Known parser data errors have text arguments. Configuration parser errors
    also hold their diagnostic text in their arguments; their raw source buffers,
    error lists and Unicode decoder objects are deliberately excluded.
    """
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
    if error_type not in (*_DATA_ERRORS, *_IO_ERRORS):
        return None
    message = parse_error_text(error)
    fresh: BaseException
    if error_type in _DATA_ERRORS:
        fresh = error_type(message)
    else:
        assert isinstance(error, OSError)
        # Builtin IO constructors preserve errno and both filenames. Windows
        # accepts winerror in the fourth position; other platforms ignore None.
        filename = error.filename
        filename2 = error.filename2
        if filename is not None and type(filename) is not str:
            return None
        if filename2 is not None and type(filename2) is not str:
            return None
        filename = bounded_parse_text(filename, MAX_INPUT_LENGTH) if filename else filename
        filename2 = bounded_parse_text(filename2, MAX_INPUT_LENGTH) if filename2 else filename2
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
