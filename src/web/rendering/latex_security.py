"""Neutralize untrusted text before a Matplotlib figure reaches TeX."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex_text(text: str) -> str:
    """Escape every TeX control character, including command backslashes."""
    return "".join(_LATEX_ESCAPES.get(char, char) for char in text)


@contextmanager
def escaped_figure_text(fig: Any) -> Iterator[None]:
    """Temporarily escape every Matplotlib Text artist in a figure."""
    from matplotlib.text import Text

    originals: list[tuple[Text, str]] = []
    for artist in fig.findobj(match=Text):
        original = artist.get_text()
        escaped = escape_latex_text(original)
        if escaped != original:
            originals.append((artist, original))
            artist.set_text(escaped)
    try:
        yield
    finally:
        for artist, original in originals:
            artist.set_text(original)


@contextmanager
def disabled_figure_usetex(fig: Any) -> Iterator[None]:
    """Temporarily force all existing Text artists away from external TeX."""
    from matplotlib.text import Text

    originals: list[tuple[Text, bool]] = []
    for artist in fig.findobj(match=Text):
        original = bool(artist.get_usetex())
        originals.append((artist, original))
        artist.set_usetex(False)
    try:
        yield
    finally:
        for artist, original in originals:
            artist.set_usetex(original)
