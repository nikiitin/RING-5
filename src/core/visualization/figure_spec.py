"""
Top-level FigureSpec and shared dimension / separator sub-specs.

``FigureSpec`` is the canonical, engine-agnostic description of a figure.
Both the Plotly and matplotlib connectors read from it; neither modifies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


# ────────────────────────────────────────────────────────────────────
# Margins
# ────────────────────────────────────────────────────────────────────

@dataclass
class MarginsSpec:
    """Figure margins in **points** (1 pt ≈ 1/72 inch).

    Both Plotly and matplotlib understand points.  Plotly converts
    internally when ``px`` are needed (1 px ≈ 1 pt at 72 dpi).
    """

    top: float = 40.0
    bottom: float = 80.0
    left: float = 60.0
    right: float = 30.0
    pad: float = 0.0  # inner padding between axes and plot area

    def to_dict(self) -> Dict[str, float]:
        """Serialize to a plain dictionary."""
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
            "pad": self.pad,
        }


# ────────────────────────────────────────────────────────────────────
# Dimensions
# ────────────────────────────────────────────────────────────────────

@dataclass
class DimensionsSpec:
    """Physical dimensions of the figure.

    ``width`` and ``height`` are in **inches** (the publication unit).
    Plotly connector converts to pixels via ``dpi``.
    """

    width: float = 7.0  # inches — default single-column IEEE
    height: float = 4.0  # inches
    dpi: int = 300  # dots-per-inch for raster output
    margins: MarginsSpec = field(default_factory=MarginsSpec)
    bar_width_scale: float = 1.0  # multiplier for bar width (matplotlib)
    bargap: float = 0.15  # gap between bar groups (Plotly)
    bargroupgap: float = 0.1  # gap within bar groups (Plotly)


# ────────────────────────────────────────────────────────────────────
# Separators
# ────────────────────────────────────────────────────────────────────

@dataclass
class SeparatorSpec:
    """Group separator lines between bar clusters."""

    enabled: bool = False
    style: Literal["solid", "dashed", "dotted", "dashdot"] = "dashed"
    color: str = "gray"


# ────────────────────────────────────────────────────────────────────
# FigureSpec — the top-level container
# ────────────────────────────────────────────────────────────────────

@dataclass
class FigureSpec:
    """Engine-agnostic, complete description of a figure.

    This is the **single source of truth** that both the Plotly and
    matplotlib connectors consume.  It owns every rendering parameter.

    Workflow:
        1. Build from user config  (PlotlyFigureSpecBuilder)
        2. Optionally overlay a preset (PresetSpecBuilder)
        3. Resolve sentinels       (resolve_spec)
        4. Pass to a connector     (FigureSpecToPlotly / FigureSpecToMatplotlib)
    """

    # ── Sub-specs (imported from sibling modules) ──────────────────
    # These are set to their default factories here; actual types are
    # imported at the class body level to avoid circular deps.

    # Dimensions & rendering
    dimensions: DimensionsSpec = field(default_factory=DimensionsSpec)

    # Typography  (font family + per-element sizes/bold)
    # Type: TypographySpec (from typography_spec.py)
    typography: Any = None  # replaced by post_init if None

    # Axes configuration
    # Type: AxesSpec (from axis_spec.py)
    axes: Any = None  # replaced by post_init if None

    # Legends — uniform list (legend1, legend2, legend3)
    # Type: List[LegendSpec]
    legends: List[Any] = field(default_factory=list)

    # Trace descriptions
    # Type: List[TraceSpec]
    traces: List[Any] = field(default_factory=list)

    # Text annotations
    # Type: List[AnnotationSpec]
    annotations: List[Any] = field(default_factory=list)

    # Group separators
    separator: SeparatorSpec = field(default_factory=SeparatorSpec)

    # Title
    title: str = ""

    # Backgrounds
    paper_bgcolor: str = "white"
    plot_bgcolor: str = "white"

    # LaTeX extras
    font_family: str = "serif"  # serif / sans-serif / monospace
    latex_extra_preamble: str = ""

    # Arbitrary metadata (benchmark name, seed, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize sub-specs with proper defaults if not provided."""
        # Lazy imports to avoid circular dependencies while keeping
        # type safety at runtime.
        from src.core.visualization.typography_spec import TypographySpec
        from src.core.visualization.axis_spec import AxesSpec

        if self.typography is None:
            self.typography = TypographySpec()
        if self.axes is None:
            self.axes = AxesSpec()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire spec tree to a plain dictionary.

        Useful for persistence (portfolio JSON) and debugging.
        """
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FigureSpec":
        """Reconstruct a FigureSpec from a serialized dictionary.

        Round-trip: ``FigureSpec.from_dict(spec.to_dict()) == spec``.
        """
        from src.core.visualization.typography_spec import TypographySpec
        from src.core.visualization.axis_spec import AxesSpec, AxisSpec
        from src.core.visualization.legend_spec import LegendSpec
        from src.core.visualization.annotation_spec import AnnotationSpec

        dims_data = data.get("dimensions", {})
        margins_data = dims_data.pop("margins", {}) if isinstance(dims_data, dict) else {}
        margins = MarginsSpec(**margins_data) if margins_data else MarginsSpec()
        dimensions = DimensionsSpec(margins=margins, **dims_data) if dims_data else DimensionsSpec()

        typo_data = data.get("typography", {})
        typography = TypographySpec(**typo_data) if typo_data else TypographySpec()

        axes_data = data.get("axes", {})
        axes = AxesSpec.from_dict(axes_data) if axes_data else AxesSpec()

        legends_data = data.get("legends", [])
        legends = [LegendSpec.from_dict(ld) for ld in legends_data]

        annotations_data = data.get("annotations", [])
        annotations = [AnnotationSpec(**ad) for ad in annotations_data]

        sep_data = data.get("separator", {})
        separator = SeparatorSpec(**sep_data) if sep_data else SeparatorSpec()

        return cls(
            dimensions=dimensions,
            typography=typography,
            axes=axes,
            legends=legends,
            traces=data.get("traces", []),
            annotations=annotations,
            separator=separator,
            title=data.get("title", ""),
            paper_bgcolor=data.get("paper_bgcolor", "white"),
            plot_bgcolor=data.get("plot_bgcolor", "white"),
            font_family=data.get("font_family", "serif"),
            latex_extra_preamble=data.get("latex_extra_preamble", ""),
            metadata=data.get("metadata", {}),
        )
