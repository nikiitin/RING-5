"""
Declarative widget system for visualization configuration.

Provides typed, schema-driven widget definitions that:
  - Replace hand-coded ``st.number_input`` / ``st.slider`` / ``st.selectbox`` calls
  - Bridge bidirectionally to ``FigureConfig`` fields
  - Generated Streamlit widgets from data, not code
  - Validate values at definition time, not at rendering time

The module has three layers:

    WidgetDef / Section (data)
        ↓
    WidgetRenderer (Streamlit generation)
        ↓
    ConfigBridge (FigureConfig ↔ config dict mapping)
"""

from src.web.rendering.widgets.config_bridge import ConfigBridge
from src.web.rendering.widgets.widget_def import (  # Standard sections
    AXIS_COLORS,
    BACKGROUNDS,
    DATA_LABELS,
    LAYOUT_DIMENSIONS,
    LAYOUT_MARGINS,
    LEGEND,
    LEGEND_APPEARANCE,
    LEGEND_POSITION,
    LEGEND_SIZING,
    STANDARD_SECTIONS,
    TYPOGRAPHY,
    CheckboxWidgetDef,
    ColorWidgetDef,
    NumberWidgetDef,
    SelectWidgetDef,
    SliderWidgetDef,
    TextWidgetDef,
    WidgetDef,
    WidgetSection,
)
from src.web.rendering.widgets.widget_renderer import WidgetRenderer

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
