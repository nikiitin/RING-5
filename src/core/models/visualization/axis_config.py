"""
Axis configurations — primary X, primary Y, and optional secondary Y.

This replaces scattered axis configuration across:
  - ``PlotDisplayConfig`` keys (Plotly vocabulary: tickangle, dtick, range)
  - ``PositioningConfig`` fields (matplotlib vocabulary: pad, rotation, offset)
  - ``LayoutExtractor`` output keys (x_range, y_range, x_tickvals, etc.)

The AxisConfig is engine-agnostic: it describes *what* the axis should look
like, and the connectors translate to engine-specific API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

INHERIT_F: float = -1.0


@dataclass
class AxisConfig:
    """Configuration for a single axis (x, y, or y2).

    Covers label, tick formatting, range, scale, grid, and positioning.
    """

    # ── Label ────────────────────────────────────────────────────
    label: str = ""
    label_pad: float = 10.0  # distance from tick labels (pts)
    label_position: float = 0.5  # 0=bottom/left, 0.5=center, 1=top/right
    label_standoff: int = -1  # sentinel: -1 = auto
    title_vshift: float = 0.0  # vertical shift for title annotation

    # ── Ticks ────────────────────────────────────────────────────
    tick_angle: float = 0.0  # rotation in degrees
    tick_pad: float = 5.0  # distance from axis (pts)
    tick_ha: Literal["left", "center", "right"] = "center"  # horizontal alignment
    tick_offset: float = 0.0  # horizontal offset (pts, for fine-tuning)
    tick_values: list[float | int | str] | None = None  # explicit tick positions
    tick_text: list[str] | None = None  # explicit tick labels
    tick_font_color: str = ""  # empty = inherit from theme
    show_tick_labels: bool = True
    dtick: float | None = None  # fixed tick interval

    # ── Range & Scale ────────────────────────────────────────
    range: list[float] | None = None  # [min, max] or None for auto
    scale: Literal["linear", "log"] = "linear"
    margin: float = 0.02  # margin as fraction of data range
    automargin: bool = True  # let engine auto-adjust margins

    # ── Grid ─────────────────────────────────────────────────────
    show_grid: bool = True
    grid_color: str = "#E5E5E5"
    grid_width: float = 1.0
    axis_color: str = "#444"
    axis_line_color: str = ""  # empty = inherit from axis_color
    axis_line_width: float = 1.0

    # ── Ordering ─────────────────────────────────────────────────
    category_order: list[str] | None = None  # explicit category order
    label_aliases: dict[str, str] | None = None  # tick label remapping

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AxisConfig:
        """Reconstruct from serialized dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AxesConfig:
    """Container for all axes in a figure.

    Supports primary X, primary Y, and optional secondary Y (twin axis).
    Secondary Y inherits from primary Y where sentinel values are used.
    """

    x: AxisConfig = field(default_factory=AxisConfig)
    y: AxisConfig = field(default_factory=AxisConfig)
    y2: AxisConfig | None = None  # None = no secondary Y-axis

    # ── Group labels (below X-axis) ──────────────────────────
    group_label_offset: float = -0.12  # vertical offset below axis
    group_label_alternate: bool = True  # alternate up/down
    group_label_alt_spacing: float = 0.05  # distance between levels
    group_order: list[str] | None = None  # explicit group ordering

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        result: dict[str, Any] = {
            "x": self.x.to_dict(),
            "y": self.y.to_dict(),
            "group_label_offset": self.group_label_offset,
            "group_label_alternate": self.group_label_alternate,
            "group_label_alt_spacing": self.group_label_alt_spacing,
            "group_order": self.group_order,
        }
        if self.y2 is not None:
            result["y2"] = self.y2.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AxesConfig:
        """Reconstruct from serialized dictionary."""
        x_data = data.get("x", {})
        y_data = data.get("y", {})
        y2_data = data.get("y2")

        return cls(
            x=AxisConfig.from_dict(x_data) if x_data else AxisConfig(),
            y=AxisConfig.from_dict(y_data) if y_data else AxisConfig(),
            y2=AxisConfig.from_dict(y2_data) if y2_data else None,
            group_label_offset=data.get("group_label_offset", -0.12),
            group_label_alternate=data.get("group_label_alternate", True),
            group_label_alt_spacing=data.get("group_label_alt_spacing", 0.05),
            group_order=data.get("group_order"),
        )
