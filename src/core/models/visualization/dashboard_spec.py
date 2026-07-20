"""Engine-independent configuration for a grid of existing plots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardSpec:
    # [impl->req~ring5.plots.multi-panel-dashboard~1]
    """Immutable layout contract for a multi-plot dashboard.

    Dimensions use screen pixels, matching :class:`ring5.FigureSpec`.  Renderers
    convert them to their native units while preserving the requested aspect
    ratio.  ``panel_titles`` is aligned positionally with ``plot_ids``.
    """

    plot_ids: tuple[int, ...]
    rows: int
    columns: int
    panel_titles: tuple[str, ...]
    title: str = ""
    width: int = 1200
    height: int = 800
    shared_xaxes: bool = False
    shared_yaxes: bool = False
    shared_legend: bool = True
    x_title: str = ""
    y_title: str = ""

    def __post_init__(self) -> None:
        """Reject layouts that cannot be rendered unambiguously."""
        if any(
            isinstance(plot_id, bool) or not isinstance(plot_id, int) for plot_id in self.plot_ids
        ):
            raise ValueError("Dashboard plot IDs must be integers.")
        if len(self.plot_ids) < 2:
            raise ValueError("A dashboard needs at least two plots.")
        if len(set(self.plot_ids)) != len(self.plot_ids):
            raise ValueError("A dashboard cannot contain the same plot more than once.")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.rows, self.columns, self.width, self.height)
        ):
            raise ValueError("Dashboard rows, columns, width, and height must be integers.")
        if self.rows < 1 or self.columns < 1:
            raise ValueError("Dashboard rows and columns must both be at least 1.")
        if self.rows * self.columns < len(self.plot_ids):
            raise ValueError(
                f"A {self.rows} x {self.columns} grid has too few panels for "
                f"{len(self.plot_ids)} plots."
            )
        if self.width < 320 or self.height < 240:
            raise ValueError("Dashboard dimensions must be at least 320 x 240 pixels.")
        if len(self.panel_titles) != len(self.plot_ids):
            raise ValueError("Dashboard panel_titles must contain one title per plot.")
        if any(not isinstance(title, str) for title in self.panel_titles):
            raise ValueError("Dashboard panel titles must be strings.")
