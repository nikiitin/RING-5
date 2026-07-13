"""Shared heatmap utilities for Plotly and Matplotlib renderers."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


def is_dark_cell(
    z: Sequence[Sequence[float | None]],
    row: int,
    col: int,
) -> bool:
    """True when the cell value is in the upper half of the z-value range.

    Works with nested lists (Plotly) and numpy arrays (Matplotlib).
    Handles None and NaN values.
    """
    val = z[row][col]
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False

    flat: list[float] = []
    for zrow in z:
        for v in zrow:
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                flat.append(float(v))
    if not flat:
        return False

    vmin, vmax = min(flat), max(flat)
    if vmax == vmin:
        return False
    return (float(val) - vmin) / (vmax - vmin) > 0.5


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
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
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
