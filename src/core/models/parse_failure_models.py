"""Nominal parser data failures and bounded immutable diagnostic facts."""

from dataclasses import dataclass


class ParseDataValueError(ValueError):
    """A parser input value violates its declared data contract."""


class ParseDataTypeError(TypeError):
    """A parsed record lacks fields required by its declared statistic kind."""


class ParseDataRuntimeError(RuntimeError):
    """Parser input or its owned transport cannot produce a valid result."""


class ResultAdmissionError(ValueError):
    """A finalized file violates its source-owned batch's retained-result limits."""


@dataclass(frozen=True, slots=True)
class ParseFailureFacts:
    """Text-only diagnostics retained by an expected failed worker Future."""

    source_path: str
    origin: str
    cause: str
