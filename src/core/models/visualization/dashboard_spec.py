"""Engine-independent configuration for a grid of existing plots."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DashboardSpec:
    # [impl->req~ring5.plots.multi-panel-dashboard~1]
    # [impl->req~ring5.figure.panel-composition~1]
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
    panel_labels: tuple[str, ...] = ()
    panel_captions: tuple[str, ...] = ()
    horizontal_spacing: float | None = None
    vertical_spacing: float | None = None

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
        for name, values in (
            ("panel_labels", self.panel_labels),
            ("panel_captions", self.panel_captions),
        ):
            if values and len(values) != len(self.plot_ids):
                raise ValueError(f"Dashboard {name} must contain one value per plot.")
            if any(not isinstance(value, str) for value in values):
                readable_name = name.replace("_", " ")
                raise ValueError(f"Dashboard {readable_name} must be strings.")
        self._validate_spacing("horizontal_spacing", self.horizontal_spacing, self.columns)
        self._validate_spacing("vertical_spacing", self.vertical_spacing, self.rows)

    @staticmethod
    def _validate_spacing(name: str, value: float | None, panel_count: int) -> None:
        """Validate one optional normalized gap between adjacent panels."""
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Dashboard {name} must be a number or None.")
        if not math.isfinite(value) or value < 0 or value > 0.2:
            raise ValueError(f"Dashboard {name} must be between 0 and 0.2.")
        if panel_count > 1 and value * (panel_count - 1) >= 1:
            raise ValueError(f"Dashboard {name} leaves no room for panel content.")

    @property
    def resolved_panel_labels(self) -> tuple[str, ...]:
        """Return labels aligned with every panel, using blanks when omitted."""
        return self.panel_labels or ("",) * len(self.plot_ids)

    @property
    def resolved_panel_captions(self) -> tuple[str, ...]:
        """Return captions aligned with every panel, using blanks when omitted."""
        return self.panel_captions or ("",) * len(self.plot_ids)

    @property
    def resolved_horizontal_spacing(self) -> float:
        """Return the explicit horizontal gap or the legacy deterministic default."""
        if self.horizontal_spacing is not None:
            return float(self.horizontal_spacing)
        return min(0.12, 0.18 / self.columns)

    @property
    def resolved_vertical_spacing(self) -> float:
        """Return the explicit vertical gap or the legacy deterministic default."""
        if self.vertical_spacing is not None:
            return float(self.vertical_spacing)
        return min(0.16, 0.24 / self.rows)
