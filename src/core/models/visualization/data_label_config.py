"""
Data label configuration — annotations on bars, points, and markers.

Controls how numeric value labels appear on plot traces (e.g., bar values,
point annotations). Settings map to widget section ``DATA_LABELS`` in
``widget_def.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal


@dataclass(frozen=True)
class DataLabelConfig:
    """Specification for data labels (value annotations) on plot traces.

    All fields have safe defaults that produce no visible labels when
    ``enabled`` is ``False``.

    Attributes:
        enabled: Whether data labels are shown at all.
        color_mode: How label color is determined:
            ``"auto"`` — theme default,
            ``"contrast"`` — auto-contrast against bar/marker fill,
            ``"custom"`` — use ``custom_color``.
        custom_color: Hex color when ``color_mode == "custom"``.
        font_size: Label font size in points.
        rotation: Text rotation in degrees (-90 to 90).
        position: Vertical placement relative to the data element.
        anchor: Vertical text anchor within the positioned label.
        format_string: d3-format string (e.g., ``.2f``, ``.1%``).
        display_logic: Which values to display:
            ``"all"`` — show every label,
            ``"above_threshold"`` — only values > threshold,
            ``"below_threshold"`` — only values < threshold.
        threshold: Numeric threshold for conditional display.
        size_constraint: How to handle oversized labels:
            ``"none"`` — show regardless,
            ``"inside"`` — resize or hide to fit within bars.
        auto_contrast: Whether to flip text color based on background
            luminance (only applies when ``color_mode == "contrast"``).
    """

    enabled: bool = False
    color_mode: Literal["auto", "contrast", "custom"] = "auto"
    custom_color: str = "#000000"
    font_size: int = 10
    rotation: int = 0
    position: Literal["auto", "inside", "outside"] = "auto"
    anchor: Literal["auto", "top", "middle", "bottom"] = "auto"
    format_string: str = ".2f"
    display_logic: Literal["all", "above_threshold", "below_threshold"] = "all"
    threshold: float = 0.0
    size_constraint: Literal["none", "inside"] = "none"
    auto_contrast: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary for JSON persistence."""
        return {
            "enabled": self.enabled,
            "color_mode": self.color_mode,
            "custom_color": self.custom_color,
            "font_size": self.font_size,
            "rotation": self.rotation,
            "position": self.position,
            "anchor": self.anchor,
            "format_string": self.format_string,
            "display_logic": self.display_logic,
            "threshold": self.threshold,
            "size_constraint": self.size_constraint,
            "auto_contrast": self.auto_contrast,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DataLabelConfig:
        """Deserialize from a plain dictionary.

        Args:
            data: Dictionary with spec fields. Unknown keys are ignored.

        Returns:
            New DataLabelConfig instance.
        """
        return cls(
            enabled=bool(data.get("enabled", False)),
            color_mode=data.get("color_mode", "auto"),
            custom_color=str(data.get("custom_color", "#000000")),
            font_size=int(data.get("font_size", 10)),
            rotation=int(data.get("rotation", 0)),
            position=data.get("position", "auto"),
            anchor=data.get("anchor", "auto"),
            format_string=str(data.get("format_string", ".2f")),
            display_logic=data.get("display_logic", "all"),
            threshold=float(data.get("threshold", 0.0)),
            size_constraint=data.get("size_constraint", "none"),
            auto_contrast=bool(data.get("auto_contrast", True)),
        )
