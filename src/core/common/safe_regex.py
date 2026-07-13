"""Bounded regular-expression compilation and matching."""

from __future__ import annotations

from typing import Protocol, cast

import regex

MAX_PATTERN_LENGTH = 512
MAX_INPUT_LENGTH = 4096
MATCH_TIMEOUT_SECONDS = 0.05


class SafeRegexError(ValueError):
    """A regular expression is invalid or exceeds an execution bound."""


class RegexMatch(Protocol):
    """Subset of a regex match used by extraction code."""

    def group(self, index: int = 0) -> str | None:
        """Return one captured group."""


class BoundedPattern(Protocol):
    """Compiled expression whose matches are executed with a timeout."""

    @property
    def groups(self) -> int:
        """Return the number of capture groups."""

    def search(self, value: str, *, timeout: float, concurrent: bool = False) -> RegexMatch | None:
        """Search *value* with an execution timeout."""


def compile_bounded_regex(pattern: str) -> BoundedPattern:
    """Compile a user expression after enforcing its structural limits.

    Args:
        pattern: Expression to compile.

    Returns:
        A compiled expression for use with :func:`search_bounded_regex`.

    Raises:
        SafeRegexError: The expression is empty, too long, or invalid.
    """
    if not pattern:
        raise SafeRegexError("The regular expression cannot be empty.")
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise SafeRegexError(
            f"The regular expression exceeds the {MAX_PATTERN_LENGTH}-character limit."
        )

    try:
        return cast(BoundedPattern, regex.compile(pattern))
    except (regex.error, TypeError) as exc:
        raise SafeRegexError(f"Invalid regular expression: {exc}") from exc


def search_bounded_regex(pattern: BoundedPattern, value: str) -> RegexMatch | None:
    """Search a string while bounding input size and execution time.

    Args:
        pattern: Expression returned by :func:`compile_bounded_regex`.
        value: String to search.

    Returns:
        The first match, or ``None`` when the expression does not match.

    Raises:
        SafeRegexError: The input is too long or matching exceeds the time limit.
    """
    if len(value) > MAX_INPUT_LENGTH:
        raise SafeRegexError(f"Regex input exceeds the {MAX_INPUT_LENGTH}-character limit.")

    try:
        return pattern.search(value, timeout=MATCH_TIMEOUT_SECONDS, concurrent=True)
    except TimeoutError as exc:
        timeout_ms = round(MATCH_TIMEOUT_SECONDS * 1000)
        raise SafeRegexError(f"Regular expression matching exceeded {timeout_ms} ms.") from exc
