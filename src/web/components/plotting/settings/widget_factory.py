"""Shared widget factory for plot settings components.

Provides standardized wrappers around Streamlit widgets that handle
default-value lookup from ``saved_config``, safe index calculation
for selectboxes, and consistent widget key generation.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.web.models.plot_models import PlotConfig


def select_option(
    label: str,
    options: list[str],
    config: PlotConfig,
    config_key: str,
    plot_id: int,
    *,
    widget_key: str | None = None,
    default: str | None = None,
    help: str | None = None,
    format_func: Any = None,
) -> str:
    """Render a selectbox with safe index lookup.

    Falls back to index 0 when the saved value is missing or not in *options*.
    """
    default = default or (options[0] if options else "")
    current = config.get(config_key, default)
    idx = options.index(current) if current in options else 0
    wk = widget_key or f"{config_key}_{plot_id}"
    kwargs: dict[str, Any] = {
        "label": label,
        "options": options,
        "index": idx,
        "key": wk,
    }
    if help is not None:
        kwargs["help"] = help
    if format_func is not None:
        kwargs["format_func"] = format_func
    return st.selectbox(**kwargs) or default


def numeric_input(
    label: str,
    config: PlotConfig,
    config_key: str,
    plot_id: int,
    *,
    widget_key: str | None = None,
    default: int | float = 0,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    step: int | float | None = None,
    help: str | None = None,
    format: str | None = None,
) -> int | float:
    """Render a number_input with config-based defaults."""
    value = config.get(config_key, default)
    if value is None:
        value = default
    if isinstance(default, float):
        value = float(value)
    elif isinstance(default, int):
        value = int(value)
    wk = widget_key or f"{config_key}_{plot_id}"
    kwargs: dict[str, Any] = {"label": label, "value": value, "key": wk}
    if min_value is not None:
        kwargs["min_value"] = min_value
    if max_value is not None:
        kwargs["max_value"] = max_value
    if step is not None:
        kwargs["step"] = step
    if help is not None:
        kwargs["help"] = help
    if format is not None:
        kwargs["format"] = format
    result: int | float = st.number_input(**kwargs)
    return result


def color_picker(
    label: str,
    config: PlotConfig,
    config_key: str,
    plot_id: int,
    *,
    widget_key: str | None = None,
    default: str = "#000000",
) -> str:
    """Render a color_picker with config-based default."""
    value = config.get(config_key, default)
    wk = widget_key or f"{config_key}_{plot_id}"
    result: str = st.color_picker(label, value, key=wk)
    return result


def toggle(
    label: str,
    config: PlotConfig,
    config_key: str,
    plot_id: int,
    *,
    widget_key: str | None = None,
    default: bool = False,
    help: str | None = None,
) -> bool:
    """Render a checkbox with config-based default."""
    value = config.get(config_key, default)
    wk = widget_key or f"{config_key}_{plot_id}"
    kwargs: dict[str, Any] = {"label": label, "value": value, "key": wk}
    if help is not None:
        kwargs["help"] = help
    result: bool = st.checkbox(**kwargs)
    return result


def slider(
    label: str,
    config: PlotConfig,
    config_key: str,
    plot_id: int,
    *,
    widget_key: str | None = None,
    default: int | float = 0,
    min_value: int | float = 0,
    max_value: int | float = 100,
    step: int | float | None = None,
    help: str | None = None,
) -> int | float:
    """Render a slider with config-based default."""
    value = config.get(config_key, default)
    if isinstance(default, float):
        value = float(value)
    elif isinstance(default, int):
        value = int(value)
    wk = widget_key or f"{config_key}_{plot_id}"
    kwargs: dict[str, Any] = {
        "label": label,
        "min_value": min_value,
        "max_value": max_value,
        "value": value,
        "key": wk,
    }
    if step is not None:
        kwargs["step"] = step
    if help is not None:
        kwargs["help"] = help
    result: int | float = st.slider(**kwargs)
    return result
