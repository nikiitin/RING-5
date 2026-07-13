"""Typed exception hierarchy for the public ring5 API.

Scripts need exceptions they can catch by meaning, not by scraping mixed
``FileNotFoundError``/``ValueError``/``KeyError`` messages out of the core
layers. Everything raised by the public surface derives from
:class:`Ring5Error` (core-raised built-ins are re-wrapped at the Session
boundary with the original as ``__cause__``).
"""

from __future__ import annotations

__all__ = [
    "Ring5Error",
    "ScanError",
    "ParseError",
    "MissingStatError",
    "PipelineError",
    "ColumnNotFoundError",
    "DataValidationError",
    "PortfolioError",
    "PortfolioVersionError",
    "ExportError",
    "DependencyMissingError",
]


class Ring5Error(Exception):
    """Base class for every error the public ring5 API raises."""


class ScanError(Ring5Error):
    """Variable scanning failed (no files, or every file failed to scan)."""


class ParseError(Ring5Error):
    """Parsing failed or produced nothing."""


class MissingStatError(ParseError):
    """One or more requested statistics matched no value in any stats file.

    Per the no-fabrication rule the parser writes ``NaN`` (never 0) for a
    missing stat — this error is how a typoed stat name becomes loud
    instead of an all-NaN column discovered at plot time.

    Attributes:
        missing: The requested variable names that produced no values.
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        super().__init__(
            "No values were parsed for: "
            + ", ".join(self.missing)
            + " — check the stat names against a scan of the same tree."
        )


class PipelineError(Ring5Error):
    """A shaper-pipeline step failed or was malformed.

    Attributes:
        step_index: Zero-based index of the failing step, when known.
        shaper_type: The step's shaper type, when known.
    """

    def __init__(
        self,
        message: str,
        *,
        step_index: int | None = None,
        shaper_type: str | None = None,
    ) -> None:
        self.step_index = step_index
        self.shaper_type = shaper_type
        super().__init__(message)


class ColumnNotFoundError(Ring5Error):
    """A named column is absent from the DataFrame.

    Attributes:
        column: The missing column name.
        available: The columns that do exist.
    """

    def __init__(self, column: str, available: list[str]) -> None:
        self.column = column
        self.available = list(available)
        super().__init__(f"Column {column!r} not found. Available: {', '.join(self.available)}")


class DataValidationError(Ring5Error):
    """A data-manager operation rejected its inputs.

    Raised for validation failures beyond a missing column (which gets the
    more specific :class:`ColumnNotFoundError`) — e.g. a non-numeric column
    passed to outlier removal or seed reduction.
    """


class PortfolioError(Ring5Error):
    """Portfolio save/load/replay failed."""


class PortfolioVersionError(PortfolioError):
    """The portfolio was written by a newer RING-5 schema.

    Mirrors the core migrator's guard (raised at the Session boundary so it
    belongs to the :class:`Ring5Error` hierarchy): loading anyway would
    silently downgrade the file and destroy the newer data on re-save.
    """


class ExportError(Ring5Error):
    """Figure export failed."""


class DependencyMissingError(Ring5Error):
    """An external binary a feature needs is not installed.

    Attributes:
        binary: The missing executable (``perl``, ``xelatex``, or a
            Chrome-family browser).
        install_hint: How to get it.
    """

    def __init__(self, binary: str, install_hint: str) -> None:
        self.binary = binary
        self.install_hint = install_hint
        super().__init__(f"{binary} is required but was not found. {install_hint}")
