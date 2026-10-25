"""Canonical numbered-axis modes and annotation-legend placement."""

from collections.abc import Mapping
from typing import Any

NUMBERED_AXIS_MODES = ("Numbers", "Number legend", "Labels")
_RETIRED_KEYS = frozenset(
    {
        "numbered_xaxis",
        "show_numbered_ticks",
        "show_numbered_legend",
        "numbered_legend_size",
        "numbered_legend_bgcolor",
        "numbered_legend_x",
        "numbered_legend_y",
        "numbered_legend_columns",
    }
)


def numbered_axis_modes(config: Mapping[str, Any]) -> list[str] | None:
    """Read distinct supported modes, retaining absent versus explicitly empty.

    Raises:
        ValueError: Modes are not a list of unique allowed strings or the
            configuration contains retired numbered-axis keys.
    """
    # [impl->req~ring5.figure.numbered-xaxis~1]
    retired = sorted(_RETIRED_KEYS.intersection(config))
    if retired:
        raise ValueError(
            f"Unsupported numbered-axis keys: {', '.join(retired)}. "
            "Use numbered_xaxis_modes and legend2_/legend3_ settings."
        )
    if "numbered_xaxis_modes" not in config:
        return None
    modes = config["numbered_xaxis_modes"]
    if not isinstance(modes, list) or any(
        not isinstance(mode, str) or mode not in NUMBERED_AXIS_MODES for mode in modes
    ):
        raise ValueError(
            f"numbered_xaxis_modes must be a list containing only {list(NUMBERED_AXIS_MODES)}."
        )
    if len(modes) != len(set(modes)):
        raise ValueError("numbered_xaxis_modes must contain unique modes.")
    return list(modes)


def numbered_legend_prefix(config: Mapping[str, Any]) -> str:
    """Return the legend tier available for numbered-axis annotations."""
    if (
        config.get("dual_axis")
        and config.get("y_columns_right")
        and not config.get("unified_legend", True)
    ):
        return "legend3_"
    return "legend2_"
