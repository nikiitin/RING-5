"""Shared heatmap utilities for Plotly and Matplotlib renderers."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from src.core.models.visualization.legend_config import ColorbarConfig
from src.web.rendering._color_utils import css_color_to_matplotlib


def heatmap_colormap(colorscale: Any) -> Any:
    """Resolve a named or positioned RGBA scale for both renderers."""
    from matplotlib import colormaps
    from matplotlib.colors import LinearSegmentedColormap

    if not isinstance(colorscale, str):
        return LinearSegmentedColormap.from_list(
            "ring5_heatmap",
            [(float(position), css_color_to_matplotlib(color)) for position, color in colorscale],
        )
    names = {name.lower(): name for name in colormaps}
    return colormaps[names.get(colorscale.lower(), colorscale)]


def contrasting_text_color(rgba: Sequence[float]) -> str:
    """Choose black or white with the larger WCAG contrast ratio."""
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgba[:3]
    ]
    luminance = sum(
        weight * channel for weight, channel in zip((0.2126, 0.7152, 0.0722), linear, strict=True)
    )
    return "black" if (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) else "white"


def heatmap_text_colors(
    z: Sequence[Sequence[float | None]],
    colorscale: Any = "Viridis",
    vmin: float | None = None,
    vmax: float | None = None,
) -> list[list[str]]:
    """Resolve cell text colors using one colormap and normalization per matrix."""
    from matplotlib.colors import Normalize

    finite = [
        float(value)
        for row in z
        for value in row
        if value is not None and math.isfinite(float(value))
    ]
    lower = min(finite, default=0.0) if vmin is None else vmin
    upper = max(finite, default=1.0) if vmax is None else vmax
    colormap = heatmap_colormap(colorscale)
    normalize = Normalize(lower, upper)
    return [
        [
            (
                contrasting_text_color(colormap(normalize(float(value))))
                if value is not None and math.isfinite(float(value))
                else "black"
            )
            for value in row
        ]
        for row in z
    ]


def compute_z_extent(
    traces: Sequence[Any],
) -> tuple[float, float]:
    """Compute the global (min, max) across all heatmap traces' z-matrices.

    Args:
        traces: Sequence of objects with a ``.z`` attribute (list of lists).

    Returns:
        Tuple ``(global_min, global_max)``. Falls back to ``(0.0, 1.0)``
        if no finite values are found.
    """
    all_vals: list[float] = []
    for trace in traces:
        z = getattr(trace, "z", None)
        if z is None:
            continue
        for row in z:
            for val in row:
                if val is not None and not math.isnan(float(val)):
                    if not math.isfinite(float(val)):
                        raise ValueError("Heatmap values must be finite or missing (NaN).")
                    all_vals.append(float(val))
    if not all_vals:
        return 0.0, 1.0
    return min(all_vals), max(all_vals)


def compute_nice_range(
    data_min: float,
    data_max: float,
    nticks: int = 5,
) -> tuple[float, float, float]:
    """Compute aesthetically rounded range boundaries for N evenly-spaced ticks.

    The algorithm finds the nearest "nice" step size (1, 2, or 5 times a
    power of 10) that yields approximately *nticks* intervals, then floors
    the minimum and ceils the maximum to multiples of that step.

    Args:
        data_min: Raw minimum value from the data.
        data_max: Raw maximum value from the data.
        nticks:   Desired number of ticks (intervals = nticks - 1).

    Returns:
        Tuple ``(nice_min, nice_max, tick_step)``.
    """
    if not math.isfinite(data_min) or not math.isfinite(data_max) or data_max < data_min:
        raise ValueError("Heatmap color bounds must be finite and ordered.")
    if data_max == data_min:
        return data_min - 1.0, data_max + 1.0, 1.0

    raw_range = data_max - data_min
    raw_step = raw_range / max(nticks - 1, 1)

    # Find the magnitude (power of 10)
    magnitude = 10 ** math.floor(math.log10(abs(raw_step)))
    residual = raw_step / magnitude

    if residual <= 1.5:
        nice_step = magnitude
    elif residual <= 3.0:
        nice_step = 2.0 * magnitude
    elif residual <= 7.0:
        nice_step = 5.0 * magnitude
    else:
        nice_step = 10.0 * magnitude

    nice_min = math.floor(data_min / nice_step) * nice_step
    nice_max = math.ceil(data_max / nice_step) * nice_step

    # Ensure the original range is covered
    if nice_min > data_min:
        nice_min -= nice_step
    if nice_max < data_max:
        nice_max += nice_step

    return nice_min, nice_max, nice_step


def heatmap_ranges(
    traces: Sequence[Any], config: ColorbarConfig
) -> tuple[tuple[float, float], ...]:
    """Resolve the same shared or individual map limits before native mutation.

    Args:
        traces: Actual heatmap sources with numeric z matrices.
        config: Current resolved colorbar configuration.

    Returns:
        Ordered native limits for each source, retaining the current rounding policy.
    """
    if not traces:
        return ()
    if config.range_mode == "manual" and config.zmin is not None and config.zmax is not None:
        lower, upper = float(config.zmin), float(config.zmax)
    else:
        raw_lower, raw_upper = compute_z_extent(traces)
        lower, upper, _ = compute_nice_range(raw_lower, raw_upper, config.nticks)
    if config.shared or config.range_mode == "manual":
        return tuple((lower, upper) for _ in traces)
    limits = []
    for trace in traces:
        raw_lower, raw_upper = compute_z_extent([trace])
        low, high, _ = compute_nice_range(raw_lower, raw_upper, config.nticks)
        limits.append((low, high))
    return tuple(limits)
