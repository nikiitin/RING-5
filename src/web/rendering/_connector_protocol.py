"""Styling pipeline contract for figure-spec connectors.

Documents the ordered sequence of styling operations that both
the Plotly connector (``FigureSpecToPlotly``) and the Matplotlib
connector (``FigureSpecToMatplotlib``) implement in their
``apply()`` methods.

Any new connector must apply styles in this order to guarantee
consistent rendering across engines.
"""

STYLING_PIPELINE_ORDER: tuple[str, ...] = (
    "backgrounds",
    "font_family",
    "color_palette",
    "title",
    "axis_labels",
    "axis_ticks",
    "axis_ranges",
    "axis_colors",
    "grids",
    "legends",
    "reference_lines",
    "data_labels",
    "annotations",
    "separators",
    "hatching",
    "margins",
)
