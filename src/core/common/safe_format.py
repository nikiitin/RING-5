"""Bounded numeric formatting for user-configurable plot labels."""

from __future__ import annotations

import re

MAX_FORMAT_LENGTH = 32
MAX_FORMAT_WIDTH = 64
MAX_FORMAT_PRECISION = 15

_FORMAT_RE = re.compile(
    r"^(?:(?:[^\n{}])?[<>=^])?[+\- ]?z?#?0?"
    r"(?P<width>\d{1,3})?[,_]?(?:\.(?P<precision>\d{1,2}))?[eEfFgGd%]?$"
)
_PLOTLY_TEMPLATE_RE = re.compile(r"^%\{y:(?P<spec>[^{}]*)\}$")


def normalize_numeric_format(spec: object, default: str = ".2f") -> str:
    """Return a resource-bounded numeric format spec or a safe default."""
    # [impl->req~ring5.quality.safe-output-formatting~1]
    candidate = str(spec) if spec is not None else ""
    template_match = _PLOTLY_TEMPLATE_RE.fullmatch(candidate)
    if template_match:
        candidate = template_match.group("spec")

    if not candidate or len(candidate) > MAX_FORMAT_LENGTH:
        return default
    match = _FORMAT_RE.fullmatch(candidate)
    if match is None:
        return default

    width = int(match.group("width") or 0)
    precision = int(match.group("precision") or 0)
    if width > MAX_FORMAT_WIDTH or precision > MAX_FORMAT_PRECISION:
        return default
    return candidate


def safe_format_number(value: int | float, spec: object, default: str = ".2f") -> str:
    """Format a number after bounding width, precision, and grammar."""
    # [impl->req~ring5.quality.safe-output-formatting~1]
    safe_spec = normalize_numeric_format(spec, default=default)
    try:
        return format(value, safe_spec)
    except (TypeError, ValueError):
        return format(value, default)


def plotly_numeric_template(spec: object, default: str = ".2f") -> str:
    """Build a single-value Plotly template from a bounded format spec."""
    # [impl->req~ring5.quality.safe-output-formatting~1]
    return f"%{{y:{normalize_numeric_format(spec, default=default)}}}"
