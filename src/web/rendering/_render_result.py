"""Return type for MatplotlibTraceRenderer.render()."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MatplotlibRenderResult:
    """Result from rendering traces onto matplotlib axes."""

    trace_count: int = 0
    heatmap_col_labels: list[str] | None = None
    heatmap_row_labels: list[str] | None = None
    heatmap_image: Any = None
