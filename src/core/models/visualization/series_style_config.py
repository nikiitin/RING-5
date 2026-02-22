"""
Series style configuration — per-trace styling overrides.

Controls visual properties that vary per trace (series) in multi-series
plots: line width, marker size, opacity, bar borders, and hatching.

These override the base trace styling when finer per-series control is
needed (e.g., different line widths or opacity for overlay traces).
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SeriesStyleConfig:
    r"""Per-trace styling overrides.

    Each ``SeriesStyleConfig`` maps 1:1 to a trace in the figure.  If
    ``FigureSpec.series_styles`` has fewer entries than traces, the
    remaining traces use default styling.

    Attributes:
        line_width: Line width in points (for line/scatter traces).
        marker_size: Marker diameter in points.
        opacity: Fill/marker opacity (0.0–1.0).
        bar_border_width: Border width around bars (in points).
        bar_border_color: Border color for bars (hex or named).
        hatching_pattern: Hatch pattern for bars. Empty string = no hatching.
            Values: ``/``, ``\\\\``, ``|``, ``-``, ``+``, ``x``, ``o``,
            ``O``, ``.``, ``*``.
    """

    line_width: float = 2.0
    marker_size: int = 6
    opacity: float = 1.0
    bar_border_width: float = 0.0
    bar_border_color: str = ""
    hatching_pattern: str = ""

    # Per-trace overrides (keyed by trace name in FigureSpec.trace_overrides)
    color: str = ""  # explicit trace color
    symbol: str = ""  # marker symbol (e.g., "square", "diamond")
    display_name: str = ""  # rename the trace legend entry

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
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeriesStyleConfig":
        """Deserialize from a plain dictionary.

        Args:
            data: Dictionary with spec fields. Unknown keys are ignored.

        Returns:
            New SeriesStyleConfig instance.
        """
        return cls(
            line_width=float(data.get("line_width", 2.0)),
            marker_size=int(data.get("marker_size", 6)),
            opacity=float(data.get("opacity", 1.0)),
            bar_border_width=float(data.get("bar_border_width", 0.0)),
            bar_border_color=str(data.get("bar_border_color", "")),
            hatching_pattern=str(data.get("hatching_pattern", "")),
            color=str(data.get("color", "")),
            symbol=str(data.get("symbol", "")),
            display_name=str(data.get("display_name", "")),
        )
