"""
Widget renderer — generate Streamlit widgets from declarative definitions.

``WidgetRenderer`` takes a ``WidgetSection`` (or list of sections) and:
  1. Creates appropriate ``st.*`` widgets with correct types and defaults
  2. Collects widget return values into a flat ``Dict[str, Any]``
  3. Handles key-prefix scoping to avoid Streamlit ``DuplicateWidgetID``

Usage:
    from src.core.visualization.widgets import WidgetRenderer, TYPOGRAPHY

    renderer = WidgetRenderer(key_prefix="plot_1")
    config = renderer.render_section(TYPOGRAPHY, saved_config)
    # config == {"title_font_size": 14, "xaxis_title_font_size": 12, ...}
"""

from __future__ import annotations

from typing import Any, Dict, Sequence

from src.core.visualization.widgets.widget_def import (
    CheckboxWidgetDef,
    ColorWidgetDef,
    NumberWidgetDef,
    SelectWidgetDef,
    SliderWidgetDef,
    TextWidgetDef,
    WidgetDef,
    WidgetSection,
)


class WidgetRenderer:
    """Stateless renderer: WidgetSection → Streamlit widgets → config dict.

    The renderer lazily imports ``streamlit`` so that the module can be
    imported (and tested) without a running Streamlit server.

    Args:
        key_prefix: String prepended to each widget key for uniqueness.
                    Typically includes the plot_id, e.g. ``"p3_"``.
    """

    def __init__(self, key_prefix: str = "") -> None:
        self._prefix = key_prefix

    def _widget_key(self, config_key: str) -> str:
        """Build a unique Streamlit widget key from prefix + config key."""
        return f"{self._prefix}{config_key}"

    def render_section(
        self,
        section: WidgetSection,
        saved_config: Dict[str, Any],
        use_expander: bool = True,
    ) -> Dict[str, Any]:
        """Render all widgets in a section and return collected config.

        Args:
            section: The widget section to render.
            saved_config: Existing config dict for reading defaults.
            use_expander: If True, wrap in ``st.expander()``.

        Returns:
            Dict mapping config keys to widget values.
        """
        import streamlit as st

        result: Dict[str, Any] = {}

        if use_expander:
            label = f"{section.icon} {section.label}" if section.icon else section.label
            with st.expander(label, expanded=not section.collapsed):
                for widget_def in section.widgets:
                    value = self._render_widget(widget_def, saved_config)
                    result[widget_def.key] = value
        else:
            for widget_def in section.widgets:
                value = self._render_widget(widget_def, saved_config)
                result[widget_def.key] = value

        return result

    def render_sections(
        self,
        sections: Sequence[WidgetSection],
        saved_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Render multiple sections and merge results.

        Args:
            sections: Sequence of widget sections to render.
            saved_config: Existing config dict for reading defaults.

        Returns:
            Merged dict of all widget values.
        """
        result: Dict[str, Any] = {}
        for section in sections:
            result.update(self.render_section(section, saved_config))
        return result

    def _render_widget(
        self,
        widget_def: WidgetDef,
        saved_config: Dict[str, Any],
    ) -> Any:
        """Render a single widget and return its value.

        Dispatches to the appropriate ``st.*`` call based on the
        ``WidgetDef`` subclass type.

        Args:
            widget_def: The widget definition to render.
            saved_config: Config dict for reading the current/saved value.

        Returns:
            The widget's current value.
        """
        import streamlit as st

        default = saved_config.get(widget_def.key, widget_def.default)
        key = self._widget_key(widget_def.key)
        help_text = widget_def.help_text or None

        if isinstance(widget_def, NumberWidgetDef):
            return st.number_input(
                label=widget_def.label,
                value=int(default) if widget_def.as_int else float(default),
                min_value=(
                    int(widget_def.min_value)
                    if widget_def.as_int and widget_def.min_value is not None
                    else widget_def.min_value
                ),
                max_value=(
                    int(widget_def.max_value)
                    if widget_def.as_int and widget_def.max_value is not None
                    else widget_def.max_value
                ),
                step=(
                    int(widget_def.step)
                    if widget_def.as_int and widget_def.step is not None
                    else widget_def.step
                ),
                key=key,
                help=help_text,
            )

        if isinstance(widget_def, SliderWidgetDef):
            return st.slider(
                label=widget_def.label,
                value=int(default) if isinstance(widget_def.min_value, int) else float(default),
                min_value=widget_def.min_value,
                max_value=widget_def.max_value,
                step=widget_def.step,
                key=key,
                help=help_text,
            )

        if isinstance(widget_def, SelectWidgetDef):
            options = list(widget_def.options)
            index = options.index(default) if default in options else 0
            return st.selectbox(
                label=widget_def.label,
                options=options,
                index=index,
                key=key,
                help=help_text,
            )

        if isinstance(widget_def, CheckboxWidgetDef):
            return st.checkbox(
                label=widget_def.label,
                value=bool(default),
                key=key,
                help=help_text,
            )

        if isinstance(widget_def, ColorWidgetDef):
            return st.color_picker(
                label=widget_def.label,
                value=str(default),
                key=key,
                help=help_text,
            )

        if isinstance(widget_def, TextWidgetDef):
            return st.text_input(
                label=widget_def.label,
                value=str(default),
                max_chars=widget_def.max_chars,
                key=key,
                help=help_text,
            )

        # Fallback: text input
        return st.text_input(
            label=widget_def.label,
            value=str(default),
            key=key,
            help=help_text,
        )
