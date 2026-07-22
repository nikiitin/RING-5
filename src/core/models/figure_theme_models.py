"""Typed figure-theme presets shared by the public API and web application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FigureThemeContext = Literal["paper", "presentation", "dashboard", "dark"]


@dataclass(frozen=True, slots=True)
class FigureTheme:
    """Portable, data-independent figure appearance configuration."""

    # [impl->req~ring5.figure.theme-presets~1]

    identifier: str
    name: str
    context: FigureThemeContext
    description: str
    config: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
