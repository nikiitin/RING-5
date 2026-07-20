"""Public boundary for non-destructive linked Plotly selections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import plotly.graph_objects as go

from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.web.rendering.linked_selection import apply_linked_selection as _apply

from ring5.errors import RenderError


def apply_linked_selection(
    figure: go.Figure,
    spec: LinkedSelectionSpec,
    values: Sequence[Any],
) -> go.Figure:
    # [impl->req~ring5.plots.linked-selections~1]
    """Create a highlighted or filtered Plotly figure copy.

    Args:
        figure: Dashboard or Plotly figure to transform.
        spec: Linked panel, axis, and behavior contract.
        values: Selected visible axis values.

    Returns:
        A new figure; ``figure`` remains unchanged.

    Raises:
        RenderError: The object or selection cannot be transformed.
    """
    try:
        return _apply(figure, spec, values)
    except (AttributeError, IndexError, TypeError, ValueError) as exc:
        raise RenderError(f"Could not apply linked selection: {exc}") from exc


__all__ = ["apply_linked_selection"]
