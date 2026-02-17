"""
Config bridge — bidirectional mapping between flat config dicts and FigureSpec.

``ConfigBridge`` uses the ``spec_path`` annotations on ``WidgetDef`` s to:
  - Extract values from a ``FigureSpec`` into a flat config dict
  - Update a ``FigureSpec`` from a flat config dict

This eliminates the need for manual mapping code between the UI layer
and the domain layer.

Usage:
    from src.core.visualization.widgets import ConfigBridge, TYPOGRAPHY

    bridge = ConfigBridge([TYPOGRAPHY, LEGEND])
    config = bridge.spec_to_config(figure_spec)
    spec   = bridge.config_to_spec(config, base_spec=FigureSpec())
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence

from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.widgets.widget_def import WidgetSection


class ConfigBridge:
    """Bidirectional FigureSpec ↔ flat config dict mapper.

    Only maps fields that have a ``spec_path`` annotation on their
    ``WidgetDef``.  Other config keys pass through untouched.

    Args:
        sections: The widget sections whose ``spec_path`` s should be mapped.
    """

    def __init__(self, sections: Sequence[WidgetSection]) -> None:
        # Build the mapping: config_key → spec_path
        self._mappings: Dict[str, str] = {}
        for section in sections:
            for widget in section.widgets:
                if widget.spec_path:
                    self._mappings[widget.key] = widget.spec_path

    @property
    def mapped_keys(self) -> List[str]:
        """Return all config keys that have a spec_path mapping."""
        return list(self._mappings.keys())

    def spec_to_config(self, spec: FigureSpec) -> Dict[str, Any]:
        """Extract a flat config dict from a FigureSpec.

        Reads each mapped ``spec_path`` from the spec and writes the
        value to the corresponding config key.

        Args:
            spec: The FigureSpec to extract values from.

        Returns:
            Flat dict with widget config keys and their values.
        """
        result: Dict[str, Any] = {}
        for config_key, path in self._mappings.items():
            value = _get_nested(spec, path)
            if value is not None:
                result[config_key] = value
        return result

    def config_to_spec(
        self,
        config: Dict[str, Any],
        base_spec: Optional[FigureSpec] = None,
    ) -> FigureSpec:
        """Update a FigureSpec from a flat config dict.

        Creates a deep copy of ``base_spec`` (or a default ``FigureSpec``)
        and sets each mapped field from the config dict.

        Args:
            config: Flat config dict from the UI widgets.
            base_spec: Starting FigureSpec to update. Defaults to new instance.

        Returns:
            A new FigureSpec with mapped values applied.
        """
        spec = copy.deepcopy(base_spec) if base_spec else FigureSpec()
        for config_key, path in self._mappings.items():
            if config_key in config:
                _set_nested(spec, path, config[config_key])
        return spec


def _get_nested(obj: Any, path: str) -> Any:
    """Get a nested attribute by dot-separated path.

    Supports integer indices for list access (e.g., "legends.0.font_size").

    Args:
        obj: The root object.
        path: Dot-separated attribute path.

    Returns:
        The value at the path, or None if any segment fails.
    """
    current = obj
    for segment in path.split("."):
        if current is None:
            return None
        if segment.isdigit():
            idx = int(segment)
            if isinstance(current, (list, tuple)) and idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            current = getattr(current, segment, None)
    return current


def _set_nested(obj: Any, path: str, value: Any) -> None:
    """Set a nested attribute by dot-separated path.

    Supports integer indices for list access (e.g., "legends.0.font_size").

    Args:
        obj: The root object.
        path: Dot-separated attribute path.
        value: The value to set.
    """
    segments = path.split(".")
    current = obj
    for i, segment in enumerate(segments[:-1]):
        if segment.isdigit():
            idx = int(segment)
            if isinstance(current, (list, tuple)) and idx < len(current):
                current = current[idx]
            else:
                return
        else:
            next_obj = getattr(current, segment, None)
            if next_obj is None:
                return
            current = next_obj

    # Set the final attribute
    last = segments[-1]
    if last.isdigit():
        idx = int(last)
        if isinstance(current, list) and idx < len(current):
            current[idx] = value
    else:
        if hasattr(current, last):
            setattr(current, last, value)
