"""
Top-level FigureConfig and shared dimension sub-specs.

``FigureConfig`` is the canonical, engine-agnostic description of a figure.
Both the Plotly and matplotlib connectors read from it; neither modifies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from src.core.models.visualization.annotation_config import (
        AnnotationConfig,
        ReferenceLineConfig,
    )
    from src.core.models.visualization.axis_config import AxesConfig
    from src.core.models.visualization.data_label_config import DataLabelConfig
    from src.core.models.visualization.legend_config import LegendConfig
    from src.core.models.visualization.series_style_config import SeriesStyleConfig
    from src.core.models.visualization.trace_config import TraceConfig
    from src.core.models.visualization.typography_config import TypographyConfig


# Margins


@dataclass(frozen=True)
class MarginsConfig:
    """Figure margins in **points** (1 pt ≈ 1/72 inch).

    Both Plotly and matplotlib understand points.  Plotly converts
    internally when ``px`` are needed (1 px ≈ 1 pt at 72 dpi).
    """

    top: float = 40.0
    bottom: float = 80.0
    left: float = 60.0
    right: float = 30.0
    pad: float = 0.0  # inner padding between axes and plot area

    def to_dict(self) -> dict[str, float]:
        """Serialize to a plain dictionary."""
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
            "pad": self.pad,
        }


# Dimensions


@dataclass(frozen=True)
class DimensionConfig:
    """Physical dimensions of the figure.

    ``width`` and ``height`` are in **inches** (the publication unit).
    Plotly connector converts to pixels via ``dpi``.
    """

    width: float = 7.0  # inches — default single-column IEEE
    height: float = 4.0  # inches
    dpi: int = 300  # dots-per-inch for raster output
    margins: MarginsConfig = field(default_factory=MarginsConfig)
    bar_width_scale: float = 1.0  # multiplier for bar width (matplotlib)
    bargap: float = 0.15  # gap between bar groups (Plotly)
    bargroupgap: float = 0.1  # gap within bar groups (Plotly)


# FigureConfig — the top-level container


@dataclass(frozen=True)
class FigureConfig:
    """Engine-agnostic, complete description of a figure.

    This is the **single source of truth** that both the Plotly and
    matplotlib connectors consume.  It owns every rendering parameter.

    Workflow:
        1. Build from user config  (PlotlyFigureSpecBuilder / ConfigSpecBuilder)
        2. Resolve sentinels       (config_resolver.resolve_config)
        3. Pass to a connector     (FigureSpecToPlotly / FigureSpecToMatplotlib)
    """

    # Sub-specs (imported from sibling modules)
    # These are set to their default factories here; actual types are
    # imported at the class body level to avoid circular deps.

    # Dimensions & rendering
    dimensions: DimensionConfig = field(default_factory=DimensionConfig)

    # Typography  (font family + per-element sizes/bold)
    typography: TypographyConfig = field(default=cast(Any, None))  # replaced by post_init

    # Axes configuration
    axes: AxesConfig = field(default=cast(Any, None))  # replaced by post_init

    # Legends — uniform list (legend1, legend2, legend3)
    legends: list[LegendConfig] = field(default_factory=list)

    # Trace descriptions
    traces: list[TraceConfig] = field(default_factory=list)

    # Text annotations
    annotations: list[AnnotationConfig] = field(default_factory=list)

    # Data labels (value annotations on bars/points)
    data_labels: DataLabelConfig | None = None

    # Per-trace styling overrides
    series_styles: list[SeriesStyleConfig] = field(default_factory=list)

    # Per-trace overrides keyed by trace name (e.g., {"trace_A": ...})
    trace_overrides: dict[str, SeriesStyleConfig] = field(default_factory=dict)

    # Color palette (Wong colorblind-safe by default)
    color_palette: list[str] = field(
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
    hatching_sequence: list[str] = field(
        default_factory=lambda: ["/", "\\", "|", "-", "+", "x", "o", "O"]
    )

    # Reference lines (horizontal/vertical baselines, thresholds)
    reference_lines: list[ReferenceLineConfig] = field(default_factory=list)

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
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize sub-specs with proper defaults if not provided."""
        # Lazy imports to avoid circular dependencies while keeping
        # type safety at runtime.
        from src.core.models.visualization.axis_config import AxesConfig
        from src.core.models.visualization.typography_config import TypographyConfig

        if self.typography is None:
            object.__setattr__(self, "typography", TypographyConfig())
        if self.axes is None:
            object.__setattr__(self, "axes", AxesConfig())

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire spec tree to a plain dictionary.

        Useful for persistence (portfolio JSON) and debugging.
        """
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FigureConfig:
        """Reconstruct a FigureConfig from a serialized dictionary.

        Nested config fields (axes / legends / series_styles / reference_lines
        / data_labels) are rebuilt into their dataclasses; ``traces`` are kept
        as the raw dicts that ``to_dict`` produced — their concrete TraceConfig
        subclasses are not reconstructed — so a round-trip preserves field
        values but is not object-identical for traces.
        """
        from src.core.models.visualization.annotation_config import (
            AnnotationConfig,
            ReferenceLineConfig,
        )
        from src.core.models.visualization.axis_config import AxesConfig
        from src.core.models.visualization.data_label_config import DataLabelConfig
        from src.core.models.visualization.legend_config import LegendConfig
        from src.core.models.visualization.series_style_config import SeriesStyleConfig
        from src.core.models.visualization.typography_config import TypographyConfig

        # Shallow-copy the nested dict before .pop() so we never mutate the
        # caller's input (from_dict must be side-effect free for round-trips).
        dims_raw = data.get("dimensions", {})
        dims_data = dict(dims_raw) if isinstance(dims_raw, dict) else {}
        margins_data = dims_data.pop("margins", {})
        margins = MarginsConfig(**margins_data) if margins_data else MarginsConfig()
        # Always pass margins — the old ``if dims_data`` short-circuit dropped parsed margins
        # when ``dimensions`` carried only a ``margins`` key.
        dimensions = DimensionConfig(margins=margins, **dims_data)

        typo_data = data.get("typography", {})
        # Filter to known fields so a legacy portfolio carrying since-removed keys
        # (e.g. the old legend3 font-size fields) loads instead of raising TypeError.
        typo_fields = TypographyConfig.__dataclass_fields__
        typo_kwargs = {k: v for k, v in typo_data.items() if k in typo_fields}
        typography = TypographyConfig(**typo_kwargs) if typo_kwargs else TypographyConfig()

        axes_data = data.get("axes", {})
        axes = AxesConfig.from_dict(axes_data) if axes_data else AxesConfig()

        legends_data = data.get("legends", [])
        legends = [LegendConfig.from_dict(ld) for ld in legends_data]

        annotations_data = data.get("annotations", [])
        annotations = [AnnotationConfig(**ad) for ad in annotations_data]

        dl_data = data.get("data_labels")
        data_labels = DataLabelConfig.from_dict(dl_data) if isinstance(dl_data, dict) else None

        ss_data = data.get("series_styles", [])
        series_styles = [SeriesStyleConfig.from_dict(sd) for sd in ss_data if isinstance(sd, dict)]

        to_raw = data.get("trace_overrides", {})
        trace_overrides: dict[str, SeriesStyleConfig] = {
            k: SeriesStyleConfig.from_dict(v) for k, v in to_raw.items() if isinstance(v, dict)
        }

        rl_data = data.get("reference_lines", [])
        reference_lines = [ReferenceLineConfig(**rd) for rd in rl_data if isinstance(rd, dict)]

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
