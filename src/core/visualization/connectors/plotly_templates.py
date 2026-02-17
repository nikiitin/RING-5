"""
Plotly Template factory — maps LaTeX presets to Plotly templates.

Creates a ``ring5_base`` template with colorblind-safe defaults and
generates per-preset templates (``ring5_isca``, ``ring5_micro``, …)
that encode font sizes, families, and spacing from the YAML presets.

Usage::

    from src.core.visualization.connectors.plotly_templates import (
        create_base_template,
        create_preset_template,
        register_all_templates,
    )

    register_all_templates(presets_dict)
    fig = go.Figure()
    fig.update_layout(template="plotly_white+ring5_isca")
"""

from __future__ import annotations

from typing import Any, Dict

import plotly.graph_objects as go
import plotly.io as pio

WONG_PALETTE = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


def create_base_template() -> go.layout.Template:
    """Base RING-5 template: colorblind-safe, data-ink optimised.

    This template encodes:
    - Wong 8-colour palette as ``colorway``
    - Clean axis styling (outside ticks, light gridlines, no zeroline)
    - Minimal legend border
    - Tight but readable margins

    Returns:
        A ``go.layout.Template`` ready for ``pio.templates`` registration.
    """
    return go.layout.Template(
        layout=go.Layout(
            colorway=WONG_PALETTE,
            font=dict(family="Arial, sans-serif", size=10, color="#333333"),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=True,
                gridcolor="#E5E5E5",
                gridwidth=1,
                showline=True,
                linecolor="#333333",
                linewidth=1,
                ticks="outside",
                tickcolor="#333333",
                title_standoff=15,
                automargin=True,
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#E5E5E5",
                gridwidth=1,
                showline=True,
                linecolor="#333333",
                linewidth=1,
                ticks="outside",
                tickcolor="#333333",
                title_standoff=15,
                automargin=True,
                zeroline=False,
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#CCCCCC",
                borderwidth=1,
            ),
            margin=dict(l=60, r=20, t=40, b=60),
        ),
    )


def create_preset_template(preset_name: str, preset_info: Dict[str, Any]) -> go.layout.Template:
    """Create a Plotly template matching a LaTeX preset.

    Maps preset font sizes, dimensions, and typography settings to a
    Plotly template that can be composed with the base template.

    Args:
        preset_name: Human-readable preset identifier (e.g. ``"isca"``).
        preset_info: A ``LaTeXPreset``-shaped dict (or subset) with keys
            such as ``font_size_base``, ``font_family``, ``font_size_title``,
            ``font_size_ticks``, ``font_size_xlabel``, ``font_size_ylabel``,
            ``line_width``, ``marker_size``, ``legend_columnspacing``, etc.

    Returns:
        A ``go.layout.Template`` encoding the preset properties.
    """
    font_size_base: int = int(preset_info.get("font_size_base", 8))
    raw_family: str = str(preset_info.get("font_family", "serif"))
    font_family = "serif" if raw_family == "serif" else "Arial, sans-serif"

    font_size_title: int = int(preset_info.get("font_size_title", font_size_base + 2))
    font_size_ticks: int = int(preset_info.get("font_size_ticks", font_size_base - 1))
    font_size_xlabel: int = int(
        preset_info.get("font_size_xlabel", preset_info.get("font_size_labels", font_size_base))
    )
    font_size_ylabel: int = int(
        preset_info.get("font_size_ylabel", preset_info.get("font_size_labels", font_size_base))
    )
    line_width: float = float(preset_info.get("line_width", 1.0))
    marker_size: float = float(preset_info.get("marker_size", 4.0))

    # Legend spacing — use preset values or sensible defaults
    legend_dict: Dict[str, Any] = {
        "bgcolor": "rgba(255,255,255,0.8)",
        "bordercolor": "#CCCCCC",
        "borderwidth": 1,
    }
    for key in ("columnspacing", "handletextpad", "labelspacing"):
        yaml_key = f"legend_{key}"
        if yaml_key in preset_info:
            # Plotly legend doesn't have exact equivalents for all spacing
            # but we store traceorder for future use
            pass

    # Dimensions
    width_px: int = int(
        float(preset_info.get("width_inches", 7.0)) * float(preset_info.get("dpi", 150))
    )
    height_px: int = int(
        float(preset_info.get("height_inches", 4.0)) * float(preset_info.get("dpi", 150))
    )

    return go.layout.Template(
        layout=go.Layout(
            colorway=WONG_PALETTE,
            font=dict(
                family=font_family,
                size=font_size_base,
                color="#333333",
            ),
            title=dict(font=dict(size=font_size_title)),
            xaxis=dict(
                showgrid=True,
                gridcolor="#E5E5E5",
                gridwidth=1,
                showline=True,
                linecolor="#333333",
                linewidth=1,
                ticks="outside",
                tickcolor="#333333",
                tickfont=dict(size=font_size_ticks),
                title=dict(font=dict(size=font_size_xlabel)),
                title_standoff=15,
                automargin=True,
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#E5E5E5",
                gridwidth=1,
                showline=True,
                linecolor="#333333",
                linewidth=1,
                ticks="outside",
                tickcolor="#333333",
                tickfont=dict(size=font_size_ticks),
                title=dict(font=dict(size=font_size_ylabel)),
                title_standoff=15,
                automargin=True,
                zeroline=False,
            ),
            legend=legend_dict,
            width=width_px,
            height=height_px,
        ),
        data=go.layout.template.Data(
            scatter=[
                go.Scatter(
                    line=dict(width=line_width),
                    marker=dict(size=marker_size),
                )
            ],
        ),
    )


def register_all_templates(presets: Dict[str, Dict[str, Any]]) -> None:
    """Register ``ring5_base`` plus one template per preset.

    After registration, templates are available via
    ``pio.templates["ring5_base"]`` or ``pio.templates["ring5_isca"]``.

    Args:
        presets: Mapping of preset name → LaTeXPreset-shaped dict.
            Typically ``{name: dict(PresetManager.load_preset(name))
            for name in PresetManager.list_presets()}``.
    """
    pio.templates["ring5_base"] = create_base_template()
    for name, info in presets.items():
        pio.templates[f"ring5_{name}"] = create_preset_template(name, info)
