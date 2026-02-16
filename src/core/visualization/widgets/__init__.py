"""
Declarative widget system for visualization configuration.

Provides typed, schema-driven widget definitions that:
  - Replace hand-coded ``st.number_input`` / ``st.slider`` / ``st.selectbox`` calls
  - Bridge bidirectionally to ``FigureSpec`` fields
  - Generated Streamlit widgets from data, not code
  - Validate values at definition time, not at rendering time

The module has three layers:

    WidgetDef / Section (data)
        ↓
    WidgetRenderer (Streamlit generation)
        ↓
    ConfigBridge (FigureSpec ↔ config dict mapping)
"""

from src.core.visualization.widgets.widget_def import (
    WidgetDef,
    WidgetSection,
    NumberWidgetDef,
    SliderWidgetDef,
    SelectWidgetDef,
    CheckboxWidgetDef,
    ColorWidgetDef,
    TextWidgetDef,
    # Standard sections
    LAYOUT_DIMENSIONS,
    LAYOUT_MARGINS,
    TYPOGRAPHY,
    BACKGROUNDS,
    AXIS_COLORS,
    LEGEND,
    LEGEND_POSITION,
    LEGEND_APPEARANCE,
    LEGEND_SIZING,
    DATA_LABELS,
    STANDARD_SECTIONS,
)
from src.core.visualization.widgets.widget_renderer import WidgetRenderer
from src.core.visualization.widgets.config_bridge import ConfigBridge

__all__ = [
    "WidgetDef",
    "WidgetSection",
    "NumberWidgetDef",
    "SliderWidgetDef",
    "SelectWidgetDef",
    "CheckboxWidgetDef",
    "ColorWidgetDef",
    "TextWidgetDef",
    "WidgetRenderer",
    "ConfigBridge",
    "LAYOUT_DIMENSIONS",
    "LAYOUT_MARGINS",
    "TYPOGRAPHY",
    "BACKGROUNDS",
    "AXIS_COLORS",
    "LEGEND",
    "LEGEND_POSITION",
    "LEGEND_APPEARANCE",
    "LEGEND_SIZING",
    "DATA_LABELS",
    "STANDARD_SECTIONS",
]
