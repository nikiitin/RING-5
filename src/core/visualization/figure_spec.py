"""
Top-level FigureSpec and shared dimension / separator sub-specs.

``FigureSpec`` is the canonical, engine-agnostic description of a figure.
Both the Plotly and matplotlib connectors read from it; neither modifies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from src.core.visualization.annotation_spec import AnnotationSpec, ReferenceLineSpec
    from src.core.visualization.axis_spec import AxesSpec
    from src.core.visualization.data_label_spec import DataLabelSpec
    from src.core.visualization.legend_spec import LegendSpec
    from src.core.visualization.series_style_spec import SeriesStyleSpec
    from src.core.visualization.trace_spec import TraceSpec
    from src.core.visualization.typography_spec import TypographySpec


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
    typography: Optional[TypographySpec] = None  # replaced by post_init if None

    # Axes configuration
    axes: Optional[AxesSpec] = None  # replaced by post_init if None

    # Legends — uniform list (legend1, legend2, legend3)
    legends: List[LegendSpec] = field(default_factory=list)

    # Trace descriptions
    traces: List[TraceSpec] = field(default_factory=list)

    # Text annotations
    annotations: List[AnnotationSpec] = field(default_factory=list)

    # Group separators
    separator: SeparatorSpec = field(default_factory=SeparatorSpec)

    # Data labels (value annotations on bars/points)
    data_labels: Optional[DataLabelSpec] = None

    # Per-trace styling overrides
    series_styles: List[SeriesStyleSpec] = field(default_factory=list)

    # Per-trace overrides keyed by trace name (e.g., {"trace_A": ...})
    trace_overrides: Dict[str, SeriesStyleSpec] = field(default_factory=dict)

    # Color palette (Wong colorblind-safe by default)
    color_palette: List[str] = field(
        default_factory=lambda: [
            "#000000",
            "#E69F00",
            "#56B4E9",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
        ]
    )

    # Bar layout mode (how multiple bar traces are arranged)
    barmode: Literal["group", "stack", "overlay", "relative"] = "group"

    # Hatching sequence for B&W-friendly bar differentiation
    hatching_sequence: List[str] = field(
        default_factory=lambda: ["/", "\\", "|", "-", "+", "x", "o", "O"]
    )

    # Reference lines (horizontal/vertical baselines, thresholds)
    reference_lines: List[ReferenceLineSpec] = field(default_factory=list)

    # Hover / interactivity
    hovermode: str = "x unified"

    # Visual features
    enable_stripes: bool = False
    show_error_bars: bool = False

    # Title
    title: str = ""

    # Backgrounds
    paper_bgcolor: str = "white"
    plot_bgcolor: str = "white"

    # LaTeX extras
    font_family: str = "serif"  # serif / sans-serif / monospace
    latex_extra_preamble: str = ""

    # Arbitrary metadata (benchmark name, seed, etc.)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize sub-specs with proper defaults if not provided."""
        # Lazy imports to avoid circular dependencies while keeping
        # type safety at runtime.
        from src.core.visualization.axis_spec import AxesSpec
        from src.core.visualization.typography_spec import TypographySpec

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
        from src.core.visualization.annotation_spec import AnnotationSpec, ReferenceLineSpec
        from src.core.visualization.axis_spec import AxesSpec
        from src.core.visualization.data_label_spec import DataLabelSpec
        from src.core.visualization.legend_spec import LegendSpec
        from src.core.visualization.series_style_spec import SeriesStyleSpec
        from src.core.visualization.typography_spec import TypographySpec

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

        dl_data = data.get("data_labels")
        data_labels = DataLabelSpec.from_dict(dl_data) if isinstance(dl_data, dict) else None

        ss_data = data.get("series_styles", [])
        series_styles = [SeriesStyleSpec.from_dict(sd) for sd in ss_data if isinstance(sd, dict)]

        to_raw = data.get("trace_overrides", {})
        trace_overrides: Dict[str, SeriesStyleSpec] = {
            k: SeriesStyleSpec.from_dict(v) for k, v in to_raw.items() if isinstance(v, dict)
        }

        rl_data = data.get("reference_lines", [])
        reference_lines = [ReferenceLineSpec(**rd) for rd in rl_data if isinstance(rd, dict)]

        # Default color palette (Wong colorblind-safe)
        default_palette = [
            "#000000",
            "#E69F00",
            "#56B4E9",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
        ]
        default_hatching = ["/", "\\", "|", "-", "+", "x", "o", "O"]

        return cls(
            dimensions=dimensions,
            typography=typography,
            axes=axes,
            legends=legends,
            traces=data.get("traces", []),
            annotations=annotations,
            separator=separator,
            data_labels=data_labels,
            series_styles=series_styles,
            trace_overrides=trace_overrides,
            color_palette=data.get("color_palette", default_palette),
            hatching_sequence=data.get("hatching_sequence", default_hatching),
            reference_lines=reference_lines,
            hovermode=data.get("hovermode", "x unified"),
            enable_stripes=bool(data.get("enable_stripes", False)),
            show_error_bars=bool(data.get("show_error_bars", False)),
            title=data.get("title", ""),
            paper_bgcolor=data.get("paper_bgcolor", "white"),
            plot_bgcolor=data.get("plot_bgcolor", "white"),
            font_family=data.get("font_family", "serif"),
            latex_extra_preamble=data.get("latex_extra_preamble", ""),
            metadata=data.get("metadata", {}),
        )
