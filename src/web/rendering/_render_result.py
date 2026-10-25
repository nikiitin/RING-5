"""Return type for MatplotlibTraceRenderer.render()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatplotlibRenderResult:
    """Result from rendering traces onto matplotlib axes."""

    trace_count: int = 0
    heatmap_col_labels: list[str] | None = None
    heatmap_row_labels: list[str] | None = None
    heatmap_image: Any = None
    # Raw category coordinates survive tick ordering and display-label aliases.
    x_category_positions: dict[str, float] = field(default_factory=dict)
    # Native handles retain their owning neutral legend role after series restyling.
    legend_handles: dict[str, list[Any]] = field(default_factory=dict)
