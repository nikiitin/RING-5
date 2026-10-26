"""
Series style configuration — per-trace styling overrides.

Controls visual properties that vary per trace (series) in multi-series
plots: line width, marker size, opacity, bar borders, and hatching.

These override the base trace styling when finer per-series control is
needed (e.g., different line widths or opacity for overlay traces).
"""

from dataclasses import dataclass
from typing import Any

from src.core.common.plot_payload import BAR_HATCH_PATTERNS


@dataclass(frozen=True)
class SeriesStyleConfig:
    r"""Per-trace styling overrides.

    ``FigureConfig.series_styles`` cycles by the original source ordinal within
    each panel, including hidden sources. Named ``trace_overrides`` apply after
    that positional style. Display text belongs to ``FigureConfig.legend_labels``.

    Attributes:
        line_width: Line width in points (for line/scatter traces).
        marker_size: Marker diameter in points.
        opacity: Fill/marker opacity (0.0–1.0).
        bar_border_width: Border width around bars (in points).
        bar_border_color: Border color for bars (hex or named).
        hatching_pattern: Hatch override for bars. None preserves the trace's
            pattern; an empty string explicitly selects Solid.
            Values: ``/``, ``\\\\``, ``|``, ``-``, ``+``, ``x``, ``o``,
            ``O``, ``.``, ``*``.
    """

    line_width: float = 2.0
    marker_size: int = 6
    opacity: float = 1.0
    bar_border_width: float = 0.0
    bar_border_color: str = ""
    hatching_pattern: str | None = None

    # Per-trace overrides (keyed by trace name in FigureSpec.trace_overrides)
    color: str = ""  # explicit trace color
    symbol: str = ""  # marker symbol (e.g., "square", "diamond")

    def __post_init__(self) -> None:
        """Reject non-string or unsupported explicit hatch values."""
        if self.hatching_pattern is not None and (
            type(self.hatching_pattern) is not str
            or self.hatching_pattern not in BAR_HATCH_PATTERNS
        ):
            raise ValueError(
                f"hatching_pattern must be None or a string from {BAR_HATCH_PATTERNS!r}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary for JSON persistence."""
        return {
            "line_width": self.line_width,
            "marker_size": self.marker_size,
            "opacity": self.opacity,
            "bar_border_width": self.bar_border_width,
            "bar_border_color": self.bar_border_color,
            "hatching_pattern": self.hatching_pattern,
            "color": self.color,
            "symbol": self.symbol,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeriesStyleConfig":
        """Deserialize from a plain dictionary.

        Args:
            data: Dictionary with spec fields. Unknown keys are ignored.

        Returns:
            New SeriesStyleConfig instance.

        Raises:
            ValueError: A retired display field or unsupported hatch is supplied.
        """
        if "display_name" in data:
            raise ValueError("Series style display_name is unsupported. Use legend_labels.")
        return cls(
            line_width=float(data.get("line_width", 2.0)),
            marker_size=int(data.get("marker_size", 6)),
            opacity=float(data.get("opacity", 1.0)),
            bar_border_width=float(data.get("bar_border_width", 0.0)),
            bar_border_color=str(data.get("bar_border_color", "")),
            hatching_pattern=data.get("hatching_pattern"),
            color=str(data.get("color", "")),
            symbol=str(data.get("symbol", "")),
        )
