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

    def fullmatch(
        self, value: str, *, timeout: float, concurrent: bool = False
    ) -> RegexMatch | None:
        """Fully match *value* with an execution timeout."""


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


def fullmatch_bounded_regex(pattern: BoundedPattern, value: str) -> RegexMatch | None:
    """Fully match a bounded string with an execution timeout."""
    if len(value) > MAX_INPUT_LENGTH:
        raise SafeRegexError(f"Regex input exceeds the {MAX_INPUT_LENGTH}-character limit.")
    try:
        return pattern.fullmatch(value, timeout=MATCH_TIMEOUT_SECONDS, concurrent=True)
    except TimeoutError as exc:
        timeout_ms = round(MATCH_TIMEOUT_SECONDS * 1000)
        raise SafeRegexError(f"Regular expression matching exceeded {timeout_ms} ms.") from exc


def normalize_stat_pattern(pattern: str) -> str:
    r"""Return the canonical form of a bounded stat-name pattern.

    Only literal gem5 identifier characters and the generated ``\d+`` numeric
    placeholder are accepted. Literal dots may be supplied as either ``.`` or
    ``\.``. The canonical form stores literal punctuation without a leading
    backslash and retains ``\d+`` placeholders.
    """
    if not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        raise SafeRegexError("Stat filters must be between 1 and 512 characters.")

    normalized: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith(r"\d+", index):
            normalized.append(r"\d+")
            index += 3
            continue

        char = pattern[index]
        if char == "\\":
            if index + 1 < len(pattern) and pattern[index + 1] in "._:":
                char = pattern[index + 1]
                index += 2
            else:
                raise SafeRegexError("Stat filters only support the \\d+ placeholder.")
        else:
            index += 1

        if not ((char.isascii() and char.isalnum()) or char in "._:"):
            raise SafeRegexError(f"Unsupported character in stat filter: {char!r}.")
        normalized.append(char)

    return "".join(normalized)


def escape_perl_stat_filter(pattern: str) -> str:
    r"""Convert a stat-name pattern into a bounded, Perl-safe expression."""
    normalized = normalize_stat_pattern(pattern)
    segments = normalized.split(r"\d+")
    escaped = [regex.escape(segment) for segment in segments]
    return r"[0-9]+".join(escaped)


def numeric_pattern_id(pattern: str, concrete_name: str) -> str | None:
    r"""Return numeric placeholder values when a concrete stat name matches.

    Literal punctuation is normalized before the capture expression is built,
    so both ``system.cpu\d+.ipc`` and ``system\.cpu\d+\.ipc`` resolve the
    concrete name ``system.cpu0.ipc`` identically.
    """
    normalized = normalize_stat_pattern(pattern)
    if len(concrete_name) > MAX_INPUT_LENGTH:
        raise SafeRegexError(f"Stat name exceeds the {MAX_INPUT_LENGTH}-character matching limit.")
    marker = r"\d+"
    if marker not in normalized:
        return None

    capture_pattern = "([0-9]+)".join(regex.escape(part) for part in normalized.split(marker))
    matched = regex.fullmatch(capture_pattern, concrete_name)
    return "_".join(matched.groups()) if matched else None
