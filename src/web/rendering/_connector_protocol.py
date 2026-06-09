"""Styling pipeline contract for figure-spec connectors.

``STYLING_PIPELINE_ORDER`` is the set of named styling steps every connector
(``FigureSpecToPlotly``, ``FigureSpecToMatplotlib``) must implement so the two
engines produce equivalent figures. The Matplotlib connector — verified by
``test_matplotlib_implements_every_pipeline_step`` — applies them in exactly
this order via ``_apply_<step>`` methods.

Two styling operations run as a sub-phase that is not a named step here:
``_apply_series_styling`` (global per-index) and ``_apply_trace_overrides``
(per trace name). Both connectors apply them after ``color_palette`` so an
explicit per-trace colour wins over the palette, and (Matplotlib) before
``legends`` so renames reach the legend.
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
