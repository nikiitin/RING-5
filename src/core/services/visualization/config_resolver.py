"""Config resolver — sentinel resolution for ``FigureConfig`` trees.

Walks the ``FigureConfig`` tree and fills inherited values.  The sentinel
value ``-1`` (int) or ``-1.0`` (float) means "inherit from parent".  This
module resolves all sentinels in ONE pass so that downstream connectors
never see ``-1``.

Moved from ``src.core.models.visualization.resolvers`` (Phase 3.5) to
comply with P2 (strict 3-layer separation: models = data, services = logic).

Inheritance chains:
    TypographyConfig:
        font_size_base
        ├── font_size_title
        ├── font_size_xlabel
        ├── font_size_ylabel
        │   └── font_size_y2label → ylabel
        ├── font_size_ticks
        │   ├── font_size_yticks → ticks
        │   └── font_size_y2ticks → yticks
        ├── font_size_annotations
        └── font_size_legend
            ├── font_size_legend2 → legend
            └── font_size_legend3 → legend
                ├── legend3_number_fontsize → legend3
                └── legend3_text_fontsize   → legend3

    LegendConfig (secondary/tertiary inherit from primary):
        legend[0].spacing → default values
        legend[1].spacing → legend[0].spacing (where -1.0)
        legend[2].spacing → legend[0].spacing (where -1.0)

    AxisSpec (y2 inherits from y):
        y.label_pad   → default
        y2.label_pad  → y.label_pad (where -1.0)
        y2.tick_pad   → y.tick_pad  (where -1.0)

Usage::

    from src.core.services.visualization.config_resolver import resolve_config

    spec = FigureConfig(...)   # may contain -1 sentinels
    resolved = resolve_config(spec)  # all -1 replaced with concrete values
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models.visualization.figure_config import FigureConfig
    from src.core.models.visualization.legend_config import LegendConfig

SENTINEL_INT: int = -1
SENTINEL_FLOAT: float = -1.0


def resolve_config(spec: FigureConfig) -> FigureConfig:
    """Return a new FigureConfig with all sentinel values resolved.

    This function is **pure** — it does not mutate the input.

    Args:
        spec: FigureConfig that may contain sentinel values (-1 / -1.0).

    Returns:
        A deep copy with all sentinels replaced by inherited values.
    """
    resolved = deepcopy(spec)
    _resolve_typography(resolved.typography)
    _resolve_legends(resolved.legends)
    _resolve_axes(resolved.axes)
    return resolved


def _resolve_int(value: int, parent: int) -> int:
    """Resolve an integer sentinel: -1 → parent value."""
    return parent if value == SENTINEL_INT else value


def _resolve_float(value: float, parent: float) -> float:
    """Resolve a float sentinel: -1.0 → parent value."""
    return parent if value == SENTINEL_FLOAT else value


def _resolve_typography(typo: object) -> None:
    """Resolve TypographyConfig sentinel chain in-place."""
    from src.core.models.visualization.typography_config import TypographyConfig

    if not isinstance(typo, TypographyConfig):
        return

    # y2label inherits from ylabel
    typo.font_size_y2label = _resolve_int(typo.font_size_y2label, typo.font_size_ylabel)

    # yticks inherits from ticks
    typo.font_size_yticks = _resolve_int(typo.font_size_yticks, typo.font_size_ticks)
    # y2ticks inherits from yticks (already resolved)
    typo.font_size_y2ticks = _resolve_int(typo.font_size_y2ticks, typo.font_size_yticks)

    # legend2 inherits from legend
    typo.font_size_legend2 = _resolve_int(typo.font_size_legend2, typo.font_size_legend)
    # legend3 inherits from legend
    typo.font_size_legend3 = _resolve_int(typo.font_size_legend3, typo.font_size_legend)
    # legend3 sub-fields inherit from legend3 (already resolved)
    typo.legend3_number_fontsize = _resolve_int(
        typo.legend3_number_fontsize, typo.font_size_legend3
    )
    typo.legend3_text_fontsize = _resolve_int(typo.legend3_text_fontsize, typo.font_size_legend3)


def _resolve_legends(legends: list[LegendConfig]) -> None:
    """Resolve LegendConfig list: secondary/tertiary inherit from primary."""
    from src.core.models.visualization.legend_config import LegendConfig

    if not legends:
        return

    # Find primary legend (first, or first with role="primary")
    primary = legends[0]
    if not isinstance(primary, LegendConfig):
        return

    primary_spacing = primary.spacing

    for legend in legends[1:]:
        if not isinstance(legend, LegendConfig):
            continue

        # Font size: -1 → follow primary
        legend.font_size = _resolve_int(legend.font_size, primary.font_size)

        # Title font size: -1 → follow own font_size
        legend.title_font_size = _resolve_int(legend.title_font_size, legend.font_size)

        # Position: -1 → auto (keep as -1.0, connectors handle "auto")
        # But spacing inherits from primary
        _resolve_legend_spacing(legend.spacing, primary_spacing)

        # Tertiary-annotation font sizes: -1 → follow own font_size
        legend.number_fontsize = _resolve_int(legend.number_fontsize, legend.font_size)
        legend.text_fontsize = _resolve_int(legend.text_fontsize, legend.font_size)

    # Also resolve primary's own title_font_size
    primary.title_font_size = _resolve_int(primary.title_font_size, primary.font_size)
    primary.number_fontsize = _resolve_int(primary.number_fontsize, primary.font_size)
    primary.text_fontsize = _resolve_int(primary.text_fontsize, primary.font_size)


def _resolve_legend_spacing(
    spacing: object,
    parent: object,
) -> None:
    """Resolve LegendSpacingConfig sentinels from parent spacing."""
    from src.core.models.visualization.legend_config import LegendSpacingConfig

    if not isinstance(spacing, LegendSpacingConfig) or not isinstance(parent, LegendSpacingConfig):
        return

    for f in fields(spacing):
        val = getattr(spacing, f.name)
        if isinstance(val, float) and val == SENTINEL_FLOAT:
            setattr(spacing, f.name, getattr(parent, f.name))


def _resolve_axes(axes: object) -> None:
    """Resolve AxisSpec inheritance: y2 inherits from y."""
    from src.core.models.visualization.axis_config import AxesConfig

    if not isinstance(axes, AxesConfig):
        return

    if axes.y2 is None:
        return

    y = axes.y
    y2 = axes.y2

    # y2 inherits label_pad from y
    y2.label_pad = _resolve_float(y2.label_pad, y.label_pad)
    # y2 inherits tick_pad from y
    y2.tick_pad = _resolve_float(y2.tick_pad, y.tick_pad)
