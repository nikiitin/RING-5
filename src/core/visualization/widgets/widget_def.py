"""
Declarative widget definitions — typed dataclasses describing UI controls.

Each ``WidgetDef`` subclass represents a single Streamlit widget.
A ``WidgetSection`` groups related widgets under a collapsible header.

Usage:
    from src.core.visualization.widgets import NumberWidgetDef, WidgetSection

    MARGINS = WidgetSection(
        id="margins",
        label="Margins",
        widgets=[
            NumberWidgetDef(key="margin_l", label="Left", default=100, min_value=0, max_value=300),
            NumberWidgetDef(key="margin_r", label="Right", default=30, min_value=0, max_value=300),
        ],
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WidgetDef:
    """Base class for all widget definitions.

    Every widget has a unique ``key`` (used as the flat-config key and
    Streamlit widget key suffix), a human label, and a default value.

    Subclasses add type-specific constraints (min/max, options, etc.).
    """

    key: str
    label: str
    default: Any
    help_text: str = ""
    # Optional mapping to a FigureSpec field path, e.g. "dimensions.margins.left"
    spec_path: str = ""


@dataclass(frozen=True)
class NumberWidgetDef(WidgetDef):
    """``st.number_input`` — numeric entry with optional bounds."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    format_str: str = ""
    # If True, render as int; else float
    as_int: bool = True


@dataclass(frozen=True)
class SliderWidgetDef(WidgetDef):
    """``st.slider`` — slider with min/max and optional step."""

    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0


@dataclass(frozen=True)
class SelectWidgetDef(WidgetDef):
    """``st.selectbox`` — dropdown selection from a list of options."""

    options: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckboxWidgetDef(WidgetDef):
    """``st.checkbox`` — boolean toggle."""

    default: bool = False


@dataclass(frozen=True)
class ColorWidgetDef(WidgetDef):
    """``st.color_picker`` — hex color selection."""

    default: str = "#000000"


@dataclass(frozen=True)
class TextWidgetDef(WidgetDef):
    """``st.text_input`` — free-text entry."""

    default: str = ""
    max_chars: Optional[int] = None


@dataclass(frozen=True)
class WidgetSection:
    """A named group of widgets rendered under a collapsible expander.

    Sections can be nested (not recommended beyond 2 levels).
    """

    id: str
    label: str
    widgets: Tuple[WidgetDef, ...] = ()
    icon: str = ""
    collapsed: bool = True

    def keys(self) -> List[str]:
        """Return all config keys defined in this section."""
        return [w.key for w in self.widgets]

    def defaults(self) -> Dict[str, Any]:
        """Return a dict of {key: default_value} for all widgets."""
        return {w.key: w.default for w in self.widgets}

    def find(self, key: str) -> Optional[WidgetDef]:
        """Find a widget definition by key. Returns None if not found."""
        for w in self.widgets:
            if w.key == key:
                return w
        return None


# ────────────────────────────────────────────────────────────────────
# Standard sections (reusable across plot types)
# ────────────────────────────────────────────────────────────────────

LAYOUT_MARGINS = WidgetSection(
    id="margins",
    label="Margins & Spacing",
    widgets=(
        NumberWidgetDef(
            key="margin_l",
            label="Left",
            default=100,
            min_value=0,
            max_value=1000,
            step=5,
            spec_path="dimensions.margins.left",
        ),
        NumberWidgetDef(
            key="margin_r",
            label="Right",
            default=100,
            min_value=0,
            max_value=1000,
            step=5,
            spec_path="dimensions.margins.right",
        ),
        NumberWidgetDef(
            key="margin_t",
            label="Top",
            default=80,
            min_value=0,
            max_value=1000,
            step=5,
            spec_path="dimensions.margins.top",
        ),
        NumberWidgetDef(
            key="margin_b",
            label="Bottom",
            default=120,
            min_value=0,
            max_value=1000,
            step=5,
            spec_path="dimensions.margins.bottom",
        ),
        NumberWidgetDef(
            key="margin_pad",
            label="Padding",
            default=0,
            min_value=0,
            max_value=200,
            step=1,
            spec_path="dimensions.margins.pad",
            help_text="Space between axis and labels",
        ),
        CheckboxWidgetDef(
            key="automargin",
            label="Auto-Margin (Prevents Cutoff)",
            default=True,
        ),
    ),
)

LAYOUT_DIMENSIONS = WidgetSection(
    id="dimensions",
    label="Dimensions",
    widgets=(
        SliderWidgetDef(
            key="width",
            label="Width (px)",
            default=800,
            min_value=400,
            max_value=1600,
            step=50,
            spec_path="dimensions.width",
        ),
        SliderWidgetDef(
            key="height",
            label="Height (px)",
            default=500,
            min_value=300,
            max_value=1200,
            step=50,
            spec_path="dimensions.height",
        ),
    ),
)

TYPOGRAPHY = WidgetSection(
    id="typography",
    label="Typography (Font Sizes & Colors)",
    icon="✏️",
    widgets=(
        NumberWidgetDef(
            key="title_font_size",
            label="Plot Title Font Size",
            default=18,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="typography.font_size_title",
        ),
        NumberWidgetDef(
            key="xaxis_title_font_size",
            label="X-Axis Title Font Size",
            default=14,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="typography.font_size_xlabel",
        ),
        NumberWidgetDef(
            key="yaxis_title_font_size",
            label="Y-Axis Title Font Size",
            default=14,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="typography.font_size_ylabel",
        ),
        SliderWidgetDef(
            key="yaxis_title_standoff",
            label="Y-Axis Title Standoff",
            default=0,
            min_value=0,
            max_value=100,
            step=1,
            help_text="Distance between Y-axis ticks and the title.",
        ),
        SliderWidgetDef(
            key="yaxis_title_vshift",
            label="Y-Axis Title Vertical Shift",
            default=0,
            min_value=-300,
            max_value=300,
            step=1,
            help_text="Move title up (+) or down (-) along the axis.",
        ),
        NumberWidgetDef(
            key="xaxis_tickfont_size",
            label="X-Axis Tick Size",
            default=12,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="typography.font_size_ticks",
            help_text="Overwrites the basic X-axis font size in Advanced Options",
        ),
        ColorWidgetDef(
            key="xaxis_tickfont_color",
            label="X-Axis Tick Color",
            default="#444444",
            spec_path="axes.xaxis.tick_font_color",
        ),
        NumberWidgetDef(
            key="yaxis_tickfont_size",
            label="Y-Axis Tick Size",
            default=12,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="typography.font_size_yticks",
        ),
        ColorWidgetDef(
            key="yaxis_tickfont_color",
            label="Y-Axis Tick Color",
            default="#444444",
            spec_path="axes.yaxis.tick_font_color",
        ),
    ),
)

LEGEND_POSITION = WidgetSection(
    id="legend_position",
    label="Position & Orientation",
    widgets=(
        SelectWidgetDef(
            key="legend_orientation",
            label="Orientation",
            default="v",
            options=("v", "h"),
            spec_path="legends.0.orientation",
        ),
        NumberWidgetDef(
            key="legend_ncols",
            label="Columns",
            default=0,
            min_value=0,
            max_value=10,
            step=1,
            spec_path="legends.0.ncol",
            help_text="Number of legend columns. 0 = Auto (single column).",
        ),
        NumberWidgetDef(
            key="legend_col_width",
            label="Column Width (px)",
            default=150,
            min_value=0,
            max_value=500,
            step=5,
            help_text="Width of each legend column in pixels.",
        ),
        SelectWidgetDef(
            key="legend_valign",
            label="Vertical Align",
            default="middle",
            options=("middle", "top", "bottom"),
        ),
    ),
)

LEGEND_APPEARANCE = WidgetSection(
    id="legend_appearance",
    label="Appearance",
    widgets=(
        CheckboxWidgetDef(
            key="transparent_legend",
            label="Transparent Background",
            default=False,
        ),
        ColorWidgetDef(
            key="legend_bgcolor",
            label="Background Color",
            default="#ffffff",
            spec_path="legends.0.bgcolor",
        ),
        ColorWidgetDef(
            key="legend_border_color",
            label="Border Color",
            default="#000000",
            spec_path="legends.0.border_color",
        ),
        NumberWidgetDef(
            key="legend_border_width",
            label="Border Width",
            default=0,
            min_value=0,
            max_value=5,
            step=1,
            spec_path="legends.0.border_width",
        ),
        ColorWidgetDef(
            key="legend_font_color",
            label="Text Color",
            default="#000000",
            spec_path="legends.0.font_color",
        ),
        NumberWidgetDef(
            key="legend_font_size",
            label="Font Size",
            default=12,
            min_value=8,
            max_value=100,
            step=1,
            spec_path="legends.0.font_size",
        ),
        ColorWidgetDef(
            key="legend_title_font_color",
            label="Title Color",
            default="#000000",
        ),
        NumberWidgetDef(
            key="legend_title_font_size",
            label="Title Size",
            default=14,
            min_value=8,
            max_value=100,
            step=1,
        ),
    ),
)

LEGEND_SIZING = WidgetSection(
    id="legend_sizing",
    label="Sizing & Spacing",
    widgets=(
        SelectWidgetDef(
            key="legend_itemsizing",
            label="Marker Scale",
            default="constant",
            options=("constant", "trace"),
            help_text="Constant: markers are equal size. Trace: markers match plot size.",
        ),
        NumberWidgetDef(
            key="legend_itemwidth",
            label="Marker Width (px)",
            default=30,
            min_value=0,
            max_value=120,
            step=1,
            help_text="Width of legend items. 0 = auto.",
        ),
        NumberWidgetDef(
            key="legend_tracegroupgap",
            label="Item Spacing (px)",
            default=10,
            min_value=0,
            max_value=100,
            step=1,
            help_text="Vertical spacing between legend items.",
        ),
    ),
)

# Legacy combined LEGEND section — union of position + appearance
LEGEND = WidgetSection(
    id="legend",
    label="Legend",
    widgets=(
        *LEGEND_POSITION.widgets,
        *LEGEND_APPEARANCE.widgets,
        *LEGEND_SIZING.widgets,
    ),
)

BACKGROUNDS = WidgetSection(
    id="backgrounds",
    label="Backgrounds & Grid",
    widgets=(
        CheckboxWidgetDef(
            key="transparent_bg",
            label="Transparent Background",
            default=False,
            help_text="Make the plot background fully transparent.",
        ),
        ColorWidgetDef(
            key="plot_bgcolor",
            label="Plot Background",
            default="#ffffff",
            spec_path="plot_bgcolor",
        ),
        ColorWidgetDef(
            key="paper_bgcolor",
            label="Paper (Outer) Background",
            default="#ffffff",
            spec_path="paper_bgcolor",
        ),
    ),
)

AXIS_COLORS = WidgetSection(
    id="axis_colors",
    label="Axis Colors",
    widgets=(
        ColorWidgetDef(
            key="grid_color",
            label="Grid Color",
            default="#e5e5e5",
            spec_path="axes.xaxis.grid_color",
        ),
        ColorWidgetDef(
            key="axis_color",
            label="Axis Line/Tick Color",
            default="#444444",
            spec_path="axes.xaxis.axis_line_color",
        ),
    ),
)

DATA_LABELS = WidgetSection(
    id="data_labels",
    label="Data Labels (Value Annotations)",
    widgets=(
        CheckboxWidgetDef(
            key="show_values",
            label="Show Values on Plot",
            default=False,
            spec_path="data_labels.enabled",
        ),
        SelectWidgetDef(
            key="text_color_mode",
            label="Value Color Mode",
            default="auto",
            options=("auto", "contrast", "custom"),
            help_text="Auto: theme default. Contrast: white on dark, black on light.",
        ),
        ColorWidgetDef(
            key="text_color",
            label="Value Color",
            default="#000000",
        ),
        NumberWidgetDef(
            key="text_font_size",
            label="Value Font Size",
            default=10,
            min_value=6,
            max_value=40,
            step=1,
            spec_path="data_labels.font_size",
        ),
        SliderWidgetDef(
            key="text_rotation",
            label="Value Rotation",
            default=0,
            min_value=-90,
            max_value=90,
            step=15,
        ),
        SelectWidgetDef(
            key="text_position",
            label="Value Position",
            default="auto",
            options=("auto", "inside", "outside"),
        ),
        SelectWidgetDef(
            key="text_anchor",
            label="Value Anchor",
            default="auto",
            options=("auto", "top", "middle", "bottom"),
        ),
        TextWidgetDef(
            key="text_format",
            label="Number Format (d3)",
            default=".2f",
            help_text="e.g. .2f for 2 decimals, .2s for SI suffix, .1% for percent.",
        ),
        SelectWidgetDef(
            key="text_display_logic",
            label="Display Logic",
            default="all",
            options=("all", "above_threshold", "below_threshold"),
        ),
        NumberWidgetDef(
            key="text_threshold",
            label="Threshold Value",
            default=0.0,
            as_int=False,
        ),
        SelectWidgetDef(
            key="text_constraint",
            label="Size Constraint",
            default="none",
            options=("none", "inside"),
            help_text="If inside, text will be resized or hidden to fit within bars.",
        ),
    ),
)

# Collect all standard sections for easy iteration
# Note: LEGEND is a convenience aggregate — STANDARD_SECTIONS uses the
# granular sub-sections to avoid duplicate spec_path entries.
STANDARD_SECTIONS: Tuple[WidgetSection, ...] = (
    LAYOUT_DIMENSIONS,
    LAYOUT_MARGINS,
    TYPOGRAPHY,
    BACKGROUNDS,
    AXIS_COLORS,
    LEGEND_POSITION,
    LEGEND_APPEARANCE,
    LEGEND_SIZING,
    DATA_LABELS,
)

# ────────────────────────────────────────────────────────────────────
# Extended sections for pills navigation (Steps 27-28)
# ────────────────────────────────────────────────────────────────────

AXIS_X = WidgetSection(
    id="axis_x",
    label="X-Axis",
    icon="straighten",
    widgets=(
        SliderWidgetDef(
            key="xaxis_tickangle",
            label="Label Rotation",
            default=-45,
            min_value=-90,
            max_value=90,
            step=15,
            spec_path="axes.xaxis.tick_angle",
            help_text="Rotate X-axis labels to prevent overlap",
        ),
        CheckboxWidgetDef(
            key="automargin",
            label="Auto-Margin (Prevents Cutoff)",
            default=True,
            spec_path="axes.xaxis.automargin",
        ),
    ),
)

AXIS_Y = WidgetSection(
    id="axis_y",
    label="Y-Axis (Left)",
    icon="straighten",
    widgets=(
        NumberWidgetDef(
            key="yaxis_dtick",
            label="Step Size (0=auto)",
            default=0.0,
            min_value=0.0,
            as_int=False,
            spec_path="axes.yaxis.dtick",
        ),
    ),
)

AXIS_Y2 = WidgetSection(
    id="axis_y2",
    label="Y-Axis (Right)",
    icon="straighten",
    widgets=(
        NumberWidgetDef(
            key="y2axis_dtick",
            label="Step Size (0=auto)",
            default=0.0,
            min_value=0.0,
            as_int=False,
            spec_path="axes.y2axis.dtick",
        ),
    ),
)

COLORS_PALETTE = WidgetSection(
    id="colors_palette",
    label="Colors & Palette",
    icon="palette",
    widgets=(
        SelectWidgetDef(
            key="color_palette",
            label="Color Palette",
            default="Plotly",
            options=(
                "Plotly",
                "G10",
                "T10",
                "Alphabet",
                "Dark24",
                "Light24",
                "Pastel",
                "Set1",
                "Set2",
                "Set3",
                "Tableau",
                "Safe",
                "Vivid",
            ),
            spec_path="color_palette",
        ),
    ),
)

REFERENCE_LINES = WidgetSection(
    id="reference_lines",
    label="Reference Lines",
    icon="horizontal_rule",
    widgets=(
        CheckboxWidgetDef(
            key="reference_line_enabled",
            label="Show Normalizer Reference Line",
            default=False,
        ),
        NumberWidgetDef(
            key="reference_line_y",
            label="Y Position",
            default=1.0,
            as_int=False,
            help_text="Y-axis value where the line is drawn.",
        ),
        ColorWidgetDef(
            key="reference_line_color",
            label="Line Color",
            default="#FF0000",
        ),
        SliderWidgetDef(
            key="reference_line_width",
            label="Line Width",
            default=1.5,
            min_value=0.5,
            max_value=4.0,
            step=0.5,
        ),
        SelectWidgetDef(
            key="reference_line_style",
            label="Line Style",
            default="dash",
            options=("dash", "dot", "dashdot", "solid"),
        ),
    ),
)

ADVANCED_SECTION = WidgetSection(
    id="advanced",
    label="Advanced",
    icon="tune",
    widgets=(
        CheckboxWidgetDef(
            key="show_error_bars",
            label="Show Error Bars (if .sd columns exist)",
            default=False,
        ),
        CheckboxWidgetDef(
            key="enable_editable",
            label="Enable Interactive Editing",
            default=False,
            help_text="Drag legend/title and click to edit text on the plot.",
        ),
        SelectWidgetDef(
            key="download_format",
            label="Default Download Format",
            default="html",
            options=("html", "png", "pdf", "svg"),
        ),
        SelectWidgetDef(
            key="export_scale",
            label="Export Scale (Resolution)",
            default="1",
            options=("1", "2", "3"),
            help_text="1x = WYSIWYG. 3x = High Res (Publication).",
        ),
    ),
)

# Extended collection including all sections
ALL_SECTIONS: Tuple[WidgetSection, ...] = (
    *STANDARD_SECTIONS,
    AXIS_X,
    AXIS_Y,
    AXIS_Y2,
    COLORS_PALETTE,
    REFERENCE_LINES,
    ADVANCED_SECTION,
)
