"""Field admission for the current serialized plot document."""

from collections.abc import Mapping
from typing import Any

from src.core.models.visualization.export_options import validate_tex_system

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


def validate_plot_config_keys(config: Mapping[str, Any]) -> None:
    """Validate current editable plot key names without interpreting template values.

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


def validate_plot_config_values(config: Mapping[str, Any]) -> None:
    """Validate concrete common figure values.

    Raises:
        ValueError: A legend orientation or PGF compiler identifier is unsupported.
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
        validate_plot_config_keys(config)
        validate_plot_config_values(config)
