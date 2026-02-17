"""Unified preset application across engines.

Merges publication-quality preset settings onto an existing
:class:`FigureSpec` that was built from the user's plot config.

**Design**:
    The user's config provides *data-derived* fields (traces, colors,
    annotations, reference lines, etc.).  A preset provides
    *publication-derived* fields (dimensions, typography, axes styling,
    legend spacing, separators, font family).  The applicator overlays
    the latter onto the former, returning a new (immutable) spec.

Usage::

    spec = PresetApplicator.apply(config_spec, preset_dict)
    # spec now has publication-quality dims/fonts with original traces
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict

from src.core.visualization.connectors.builders import PresetSpecBuilder
from src.core.visualization.figure_spec import FigureSpec


class PresetApplicator:
    """Apply preset values onto a FigureSpec, engine-agnostic.

    This is a **stateless** service — all methods are static.

    Merge semantics:
        - **Overridden by preset**: dimensions, typography, axes, legends,
          separator, font_family, latex_extra_preamble.
        - **Kept from config spec**: traces, annotations, data_labels,
          series_styles, trace_overrides, color_palette, hatching_sequence,
          reference_lines, hovermode, enable_stripes, show_error_bars,
          title, paper_bgcolor, plot_bgcolor, metadata.
    """

    @staticmethod
    def apply(
        spec: FigureSpec,
        preset_info: Dict[str, Any],
    ) -> FigureSpec:
        """Overlay preset values onto an existing spec.

        Args:
            spec: The base spec built from the user's plot configuration
                (via :class:`ConfigSpecBuilder` or similar).
            preset_info: A ``LaTeXPreset``-shaped dictionary, typically
                loaded from the YAML preset catalogue.

        Returns:
            A **new** :class:`FigureSpec` with publication-quality
            dimensions, typography, axes, legends, separator settings
            from the preset and all data-derived fields from *spec*.
        """
        preset_spec: FigureSpec = PresetSpecBuilder.from_preset(preset_info)

        return dataclasses.replace(
            spec,
            # ── Publication-quality overrides ──────────────────
            dimensions=preset_spec.dimensions,
            typography=preset_spec.typography,
            axes=preset_spec.axes,
            legends=preset_spec.legends,
            separator=preset_spec.separator,
            font_family=preset_spec.font_family,
            latex_extra_preamble=preset_spec.latex_extra_preamble,
        )

    @staticmethod
    def apply_partial(
        spec: FigureSpec,
        preset_info: Dict[str, Any],
    ) -> FigureSpec:
        """Overlay **only explicitly-set** preset keys onto *spec*.

        Unlike :meth:`apply`, this method only overrides fields whose
        keys are actually present in *preset_info*.  Useful when the
        user has fine-tuned individual slider values and only a subset
        of preset keys should be applied.

        Args:
            spec: The base spec.
            preset_info: A partial ``LaTeXPreset``-shaped dictionary.

        Returns:
            A new :class:`FigureSpec` with selective overrides.
        """
        overrides: Dict[str, Any] = {}

        # Map preset-key groups → FigureSpec field names.
        _DIMENSION_KEYS = {
            "width_inches",
            "height_inches",
            "dpi",
            "bar_width_scale",
        }
        _TYPO_KEYS = {
            "font_size_base",
            "font_size_title",
            "font_size_xlabel",
            "font_size_ylabel",
            "font_size_y2label",
            "font_size_ticks",
            "font_size_yticks",
            "font_size_y2ticks",
            "font_size_annotations",
            "font_size_legend",
            "font_size_legend2",
            "font_size_legend3",
            "legend3_number_fontsize",
            "legend3_text_fontsize",
            "bold_title",
            "bold_xlabel",
            "bold_ylabel",
            "bold_y2label",
            "bold_ticks",
            "bold_annotations",
            "bold_group_labels",
            "bold_legend",
            "bold_legend2",
            "bold_legend3",
        }
        _AXES_KEYS = {
            "xtick_rotation",
            "xtick_pad",
            "xtick_ha",
            "xtick_offset",
            "xaxis_margin",
            "ylabel_pad",
            "ylabel_y_position",
            "ytick_pad",
            "group_label_offset",
            "group_label_alternate",
            "group_label_alt_spacing",
        }
        _LEGEND_KEYS = {
            "legend_columnspacing",
            "legend_handletextpad",
            "legend_labelspacing",
            "legend_handlelength",
            "legend_handleheight",
            "legend_borderpad",
            "legend_borderaxespad",
            "legend_ncol",
            "legend_custom_pos",
            "legend_x",
            "legend_y",
            "legend2_columnspacing",
            "legend2_handletextpad",
            "legend2_labelspacing",
            "legend2_handlelength",
            "legend2_handleheight",
            "legend2_borderpad",
            "legend2_borderaxespad",
            "legend2_ncol",
            "legend3_borderpad",
            "legend3_labelspacing",
        }
        _SEPARATOR_KEYS = {
            "group_separator",
            "group_separator_style",
            "group_separator_color",
        }

        preset_keys = set(preset_info.keys())

        # Build the full preset spec once — we only selectively pick fields.
        preset_spec: FigureSpec = PresetSpecBuilder.from_preset(preset_info)

        if preset_keys & _DIMENSION_KEYS:
            overrides["dimensions"] = preset_spec.dimensions
        if preset_keys & _TYPO_KEYS:
            overrides["typography"] = preset_spec.typography
        if preset_keys & _AXES_KEYS:
            overrides["axes"] = preset_spec.axes
        if preset_keys & _LEGEND_KEYS:
            overrides["legends"] = preset_spec.legends
        if preset_keys & _SEPARATOR_KEYS:
            overrides["separator"] = preset_spec.separator
        if "font_family" in preset_keys:
            overrides["font_family"] = preset_spec.font_family
        if "latex_extra_preamble" in preset_keys:
            overrides["latex_extra_preamble"] = preset_spec.latex_extra_preamble

        if not overrides:
            return spec

        return dataclasses.replace(spec, **overrides)
