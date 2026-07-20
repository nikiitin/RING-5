"""Accessible defaults, WCAG contrast checks, and non-color encodings."""

from __future__ import annotations

import copy
import re
from dataclasses import replace
from typing import Any, Final, cast

from src.core.models.accessibility_models import AccessibilityFinding, AccessibilityReport
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.core.services.visualization.palette_service import (
    is_colorblind_safe,
    resolve_palette,
)

_MARK_CONTRAST: Final = 3.0
_TEXT_CONTRAST: Final = 4.5
_PATTERNS: Final = ("/", "\\", "|", "-", "+", "x", "o", "O")
_MARKERS: Final = (
    "circle",
    "square",
    "diamond",
    "triangle-up",
    "x",
    "cross",
    "triangle-down",
    "star",
)
_NON_COLOR_PLOT_TYPES: Final = {
    "area",
    "bar",
    "dual_axis_bar_dot",
    "ecdf",
    "grouped_bar",
    "grouped_stacked_bar",
    "histogram",
    "line",
    "scatter",
    "stacked_bar",
}
_RGB_RE = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$")
_RGBA_RE = re.compile(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9]*\.?[0-9]+)\s*\)$")
_NAMED_COLORS: Final = {
    "black": "#000000",
    "white": "#ffffff",
    "transparent": "#ffffff",
}


class AccessibilityService:
    """Apply and audit one explicit cross-engine accessibility mode."""

    @staticmethod
    def apply_defaults(config: dict[str, Any], plot_type: str) -> dict[str, Any]:
        """Return accessible defaults when ``accessibility_mode`` is enabled."""
        # [impl->req~ring5.figure.accessible-themes~1]
        if not bool(config.get("accessibility_mode", False)):
            return config
        result = copy.deepcopy(config)
        result.setdefault("color_palette", "ring5_accessible")
        result.setdefault("paper_bgcolor", "#ffffff")
        result.setdefault("plot_bgcolor", "#ffffff")
        result.setdefault("axis_color", "#333333")
        result.setdefault("grid_color", "#d0d0d0")
        result.setdefault("xaxis_tickfont_color", "#222222")
        result.setdefault("yaxis_tickfont_color", "#222222")
        result.setdefault("legend_font_color", "#222222")
        result.setdefault("legend_title_font_color", "#111111")
        result.setdefault("title_font_size", 18)
        result.setdefault("xaxis_title_font_size", 14)
        result.setdefault("yaxis_title_font_size", 14)
        result.setdefault("xaxis_tickfont_size", 12)
        result.setdefault("yaxis_tickfont_size", 12)
        result.setdefault("legend_font_size", 12)
        result.setdefault("axis_line_width", 1.5)
        if "bar" in plot_type or plot_type == "histogram":
            result["enable_stripes"] = True
        if plot_type in {"line", "area", "ecdf", "scatter", "dual_axis_bar_dot"}:
            result["show_markers"] = True
            result["marker_size"] = max(int(result.get("marker_size", 0)), 7)
        return result

    @classmethod
    def apply_non_color_encodings(
        cls,
        result: TraceBuildResult,
        config: dict[str, Any],
    ) -> TraceBuildResult:
        """Cycle patterns and symbols on engine-independent trace values."""
        # [impl->req~ring5.figure.accessible-themes~1]
        if not bool(config.get("accessibility_mode", False)):
            return result
        traces: list[TraceConfig] = []
        for index, trace in enumerate(result.traces):
            if isinstance(trace, BarTraceConfig):
                traces.append(
                    replace(
                        trace,
                        pattern=trace.pattern or _PATTERNS[index % len(_PATTERNS)],
                        border_width=max(trace.border_width, 1.0),
                        border_color=trace.border_color or "#222222",
                    )
                )
            elif isinstance(trace, LineTraceConfig):
                traces.append(
                    replace(
                        trace,
                        show_markers=True,
                        marker_symbol=_MARKERS[index % len(_MARKERS)],
                        marker_size=max(trace.marker_size, 7),
                    )
                )
            elif isinstance(trace, ScatterTraceConfig):
                traces.append(
                    replace(
                        trace,
                        marker_symbol=_MARKERS[index % len(_MARKERS)],
                        marker_size=max(trace.marker_size, 8),
                        marker_line_width=max(trace.marker_line_width, 1.0),
                        marker_line_color=trace.marker_line_color or "#222222",
                    )
                )
            else:
                traces.append(trace)
        return replace(result, traces=traces)

    @classmethod
    def audit(
        cls,
        config: dict[str, Any],
        plot_type: str,
        *,
        series_count: int = 1,
    ) -> AccessibilityReport:
        """Validate palette safety, contrast, text size, and redundant encodings."""
        # [impl->req~ring5.figure.accessible-themes~1]
        if not isinstance(config, dict):
            raise TypeError("Figure accessibility configuration must be a dictionary.")
        if not isinstance(plot_type, str) or not plot_type.strip():
            raise ValueError("Figure accessibility requires a plot type.")
        if not isinstance(series_count, int) or isinstance(series_count, bool) or series_count < 1:
            raise ValueError("Figure accessibility series_count must be a positive integer.")
        effective = cls.apply_defaults(config, plot_type.strip())
        findings: list[AccessibilityFinding] = []
        palette_value = effective.get("color_palette", "ring5_accessible")
        palette_name = palette_value if isinstance(palette_value, str) else "custom"
        palette_safe = isinstance(palette_value, str) and is_colorblind_safe(palette_value)
        if not palette_safe:
            findings.append(
                AccessibilityFinding(
                    "error",
                    "palette",
                    "Choose a palette marked color-vision-safe or enable the accessible default.",
                )
            )

        background = cls._parse_color(str(effective.get("plot_bgcolor", "#ffffff")))
        ratios: list[float] = []
        if background is None:
            findings.append(
                AccessibilityFinding(
                    "error",
                    "plot background",
                    "Use an opaque hex or RGB plot background so contrast can be verified.",
                )
            )
        else:
            for index, color in enumerate(resolve_palette(palette_value), start=1):
                foreground = cls._parse_color(color)
                if foreground is None:
                    findings.append(
                        AccessibilityFinding(
                            "error",
                            f"palette color {index}",
                            f"Color {color!r} cannot be checked for contrast.",
                        )
                    )
                    continue
                ratio = cls._contrast(foreground, background)
                ratios.append(ratio)
                if ratio < _MARK_CONTRAST:
                    findings.append(
                        AccessibilityFinding(
                            "error",
                            f"palette color {index}",
                            f"Mark contrast must be at least {_MARK_CONTRAST:.1f}:1.",
                            round(ratio, 2),
                        )
                    )

            text_colors = {
                "axis and labels": str(effective.get("axis_color", "#333333")),
                "x tick text": str(
                    effective.get("xaxis_tickfont_color") or effective.get("axis_color", "#333333")
                ),
                "y tick text": str(
                    effective.get("yaxis_tickfont_color") or effective.get("axis_color", "#333333")
                ),
                "legend text": str(effective.get("legend_font_color", "#222222")),
            }
            paper = cls._parse_color(str(effective.get("paper_bgcolor", "#ffffff")))
            for component, color in text_colors.items():
                foreground = cls._parse_color(color)
                target_background = paper if component == "legend text" else background
                if foreground is None or target_background is None:
                    findings.append(
                        AccessibilityFinding(
                            "error",
                            component,
                            f"Text color {color!r} cannot be checked for contrast.",
                        )
                    )
                    continue
                ratio = cls._contrast(foreground, target_background)
                ratios.append(ratio)
                if ratio < _TEXT_CONTRAST:
                    findings.append(
                        AccessibilityFinding(
                            "error",
                            component,
                            f"Text contrast must be at least {_TEXT_CONTRAST:.1f}:1.",
                            round(ratio, 2),
                        )
                    )

        minimum_sizes = {
            "figure title": int(effective.get("title_font_size", 18)),
            "x axis title": int(effective.get("xaxis_title_font_size", 14)),
            "y axis title": int(effective.get("yaxis_title_font_size", 14)),
            "axis tick text": min(
                int(effective.get("xaxis_tickfont_size", 12)),
                int(effective.get("yaxis_tickfont_size", 12)),
            ),
            "legend text": int(effective.get("legend_font_size", 12)),
            "legend title": int(effective.get("legend_title_font_size", 14)),
        }
        for component, size in minimum_sizes.items():
            if size < 10:
                findings.append(
                    AccessibilityFinding(
                        "warning",
                        component,
                        "Use at least 10 pt for text that readers must decode.",
                    )
                )

        accessibility_mode = bool(effective.get("accessibility_mode", False))
        non_color = accessibility_mode and plot_type.strip() in _NON_COLOR_PLOT_TYPES
        if series_count > 1:
            if not accessibility_mode:
                findings.append(
                    AccessibilityFinding(
                        "error",
                        "series encoding",
                        "Enable accessibility mode to add patterns or marker symbols "
                        "alongside color.",
                    )
                )
            elif not non_color:
                findings.append(
                    AccessibilityFinding(
                        "error",
                        "series encoding",
                        f"{plot_type.strip()} does not yet provide a verified non-color "
                        "series encoding.",
                    )
                )
            elif series_count > min(len(_PATTERNS), len(_MARKERS)):
                findings.append(
                    AccessibilityFinding(
                        "error",
                        "series encoding",
                        "Use no more than eight series per figure so colors and redundant "
                        "encodings remain distinct.",
                    )
                )
        return AccessibilityReport(
            palette_name=palette_name,
            palette_colorblind_safe=palette_safe,
            non_color_encodings=non_color,
            minimum_contrast_ratio=round(min(ratios), 2) if ratios else None,
            findings=tuple(findings),
        )

    @staticmethod
    def contrast_ratio(foreground: str, background: str) -> float:
        """Return WCAG relative-luminance contrast for two opaque CSS colors."""
        first = AccessibilityService._parse_color(foreground)
        second = AccessibilityService._parse_color(background)
        if first is None or second is None:
            raise ValueError("Contrast colors must be opaque hex, RGB, black, or white values.")
        return AccessibilityService._contrast(first, second)

    @staticmethod
    def _parse_color(color: str) -> tuple[int, int, int] | None:
        resolved = color.strip().lower()
        resolved = _NAMED_COLORS.get(resolved, resolved)
        if re.fullmatch(r"#[0-9a-f]{3}", resolved):
            return cast(
                tuple[int, int, int],
                tuple(int(character * 2, 16) for character in resolved[1:]),
            )
        if re.fullmatch(r"#[0-9a-f]{6}", resolved):
            return cast(
                tuple[int, int, int],
                tuple(int(resolved[index : index + 2], 16) for index in (1, 3, 5)),
            )
        match = _RGB_RE.match(resolved)
        if match:
            channels = tuple(int(value) for value in match.groups())
            if all(0 <= value <= 255 for value in channels):
                return cast(tuple[int, int, int], channels)
            return None
        rgba = _RGBA_RE.match(resolved)
        if rgba and float(rgba.group(4)) == 1.0:
            channels = tuple(int(value) for value in rgba.groups()[:3])
            if all(0 <= value <= 255 for value in channels):
                return cast(tuple[int, int, int], channels)
            return None
        return None

    @staticmethod
    def _contrast(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
        def luminance(color: tuple[int, int, int]) -> float:
            channels = []
            for value in color:
                channel = value / 255.0
                channels.append(
                    channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                )
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
        return (lighter + 0.05) / (darker + 0.05)
