"""Result contract for copying configuration or pipelines between plots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlotTransferMode = Literal["settings", "configuration", "pipeline"]


@dataclass(frozen=True)
class PlotTransferResult:
    # [impl->req~ring5.plots.copy-settings-pipeline~1]
    """Immutable summary of an applied destination-only plot transfer."""

    source_plot_id: int
    target_plot_id: int
    mode: PlotTransferMode
    copied_keys: tuple[str, ...] = ()
    pipeline_steps: int = 0
    requires_finalize: bool = False


__all__ = ["PlotTransferMode", "PlotTransferResult"]
