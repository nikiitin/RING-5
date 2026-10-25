"""Field admission for the current serialized plot document."""

from collections.abc import Mapping
from typing import Any

from src.core.models.visualization.export_options import validate_tex_system

# Current editable bar patterns include Matplotlib's circle and star hatches.
BAR_HATCH_PATTERNS: tuple[str, ...] = ("", "/", "\\", "x", "-", "|", "+", ".", "o", "O", "*")

_PLOT_FIELDS = frozenset(
    {
        "id",
        "name",
        "plot_type",
        "config",
        "source_data",
        "processed_data",
        "pipeline",
        "pipeline_counter",
        "figure_spec",
    }
)


def validate_plot_config_keys(config: Mapping[str, Any], *, plot_type: str | None = None) -> None:
    """Validate current editable plot key names without interpreting template values.

    Args:
        config: Editable plot configuration or an unmaterialized recipe mapping.
        plot_type: Exact plot identifier when the caller owns that context.

    Raises:
        ValueError: A key is not text or is outside the current configuration contract.
    """
    # [impl->req~ring5.portfolio.schema~1]
    if any(not isinstance(key, str) for key in config):
        raise ValueError("Plot configuration keys must be text names.")
    unsupported = sorted(
        {"latex_extra_preamble", "download_format", "enable_editable"} & config.keys()
    )
    if unsupported:
        raise ValueError(f"Unsupported plot configuration keys: {', '.join(unsupported)}.")
    retired = sorted(
        key
        for key in config
        if key.startswith("dual_legend_")
        or key
        in {
            "legend_xanchor",
            "legend_yanchor",
            "legend2_xanchor",
            "legend2_yanchor",
            "legend3_xanchor",
            "legend3_yanchor",
        }
    )
    if retired:
        raise ValueError(
            f"Unsupported legend configuration keys: {', '.join(retired)}. "
            "Use legend_/legend2_/legend3_ fields with anchor_x/anchor_y."
        )
    if plot_type == "heatmap":
        retired_heatmap = sorted(config.keys() & {"colorscale", "show_cell_values"})
        if retired_heatmap:
            raise ValueError(
                f"Unsupported heatmap configuration keys: {', '.join(retired_heatmap)}. "
                "Use color_palette, reverse_colorscale and show_values."
            )


def validate_plot_config_values(config: Mapping[str, Any], *, plot_type: str | None = None) -> None:
    """Validate concrete common figure values.

    Args:
        config: Configuration after any recipe parameters are materialized.
        plot_type: Exact plot identifier when the caller owns that context.

    Raises:
        ValueError: A legend orientation, PGF compiler or series pattern is unsupported.
    """
    # [impl->req~ring5.api.plot-validation~1]
    if "tex_system" in config:
        validate_tex_system(config["tex_system"])
    for prefix in ("legend_", "legend2_", "legend3_"):
        key = f"{prefix}orientation"
        if key in config and (
            not isinstance(config[key], str) or config[key] not in ("horizontal", "vertical")
        ):
            raise ValueError(f"{key} must be exactly 'horizontal' or 'vertical'.")
    if "series_styles" not in config:
        return
    styles = config["series_styles"]
    if not isinstance(styles, Mapping):
        raise ValueError("series_styles must map text series names to style mappings.")
    for name, style in styles.items():
        if not isinstance(name, str) or not isinstance(style, Mapping):
            raise ValueError("series_styles must map text series names to style mappings.")
        if "pattern" in style and (
            not isinstance(style["pattern"], str) or style["pattern"] not in BAR_HATCH_PATTERNS
        ):
            raise ValueError(
                f"Series style {name!r} pattern must be a string from {BAR_HATCH_PATTERNS!r}."
            )


def validate_plot_fields(payload: dict[str, Any]) -> None:
    """Reject unsupported plot state before deserialization or publication.

    The optional figure specification records resolved styling. Editable config
    and pipeline drafts retain their current nested contracts.

    Args:
        payload: A serialized plot mapping admitted by the current portfolio format.

    Raises:
        ValueError: The document contains fields outside the current plot contract.
    """
    # [impl->req~ring5.portfolio.schema~1]
    if any(not isinstance(key, str) for key in payload):
        raise ValueError("Plot fields must have text names.")
    unknown = payload.keys() - _PLOT_FIELDS
    if unknown:
        raise ValueError(
            f"Unsupported plot fields in the current typed representation: {sorted(unknown)}."
        )
    config = payload.get("config", {})
    if isinstance(config, Mapping):
        validate_plot_config_keys(config, plot_type=payload.get("plot_type"))
        validate_plot_config_values(config, plot_type=payload.get("plot_type"))
