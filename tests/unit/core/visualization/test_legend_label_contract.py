"""Canonical labels are owned text maps independent of visual series styles."""

from copy import deepcopy
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest

from src.core.common.plot_payload import (
    validate_legend_labels,
    validate_plot_config_keys,
    validate_plot_config_values,
)
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.config_builder import ConfigSpecBuilder


@pytest.mark.parametrize("value", [None, [], "Shown", {1: "Shown"}, {"raw": 1}, {"raw": None}])
def test_label_maps_reject_nontext_values_at_each_concrete_boundary(value: Any) -> None:
    for boundary in (
        lambda: validate_legend_labels(value),
        lambda: validate_plot_config_values({"legend_labels": value}),
        lambda: FigureConfig(legend_labels=value),
        lambda: FigureConfig.from_dict({"legend_labels": value}),
        lambda: ConfigSpecBuilder.from_config({"legend_labels": value}, "bar"),
    ):
        with pytest.raises(ValueError, match="legend_labels must map text"):
            boundary()


def test_label_map_ownership_and_codec_preserve_literal_text_without_coercion() -> None:
    raw = np.str_("001")
    shown = np.str_("NA")
    supplied = {raw: shown, "A": "B", "B": "C", "_raw": "_Shown", "empty": ""}
    spec = FigureConfig(legend_labels=supplied)
    supplied[raw] = "changed"
    assert spec.legend_labels[raw] is shown
    assert next(key for key in spec.legend_labels if key == raw) is raw
    assert spec.legend_labels == {raw: shown, "A": "B", "B": "C", "_raw": "_Shown", "empty": ""}

    encoded = spec.to_dict()
    restored = FigureConfig.from_dict(encoded)
    encoded["legend_labels"]["A"] = "changed"
    assert restored.legend_labels == spec.legend_labels
    assert restored.legend_labels is not spec.legend_labels
    assert type(restored.legend_labels[raw]) is np.str_

    immutable = MappingProxyType({"raw": "Shown"})
    owned = validate_legend_labels(immutable)
    owned["raw"] = "edited"
    assert immutable["raw"] == "Shown"


def test_builder_keeps_raw_override_keys_and_owns_its_label_projection() -> None:
    config = {
        "legend_labels": {"A": "Same", "B": "Same", "inactive": "Retained"},
        "series_styles": {
            "A": {"use_color": True, "color": "#ff0000", "pattern": "/"},
            "B": {"use_color": True, "color": "#0000ff", "pattern": ""},
        },
    }
    before = deepcopy(config)
    spec = ConfigSpecBuilder.from_config(config, "bar")
    assert spec.legend_labels == config["legend_labels"]
    assert set(spec.trace_overrides) == {"A", "B"}
    assert spec.trace_overrides["A"].color == "#ff0000"
    assert spec.trace_overrides["B"].color == "#0000ff"
    assert spec.trace_overrides["A"].hatching_pattern == "/"
    assert spec.trace_overrides["B"].hatching_pattern == ""
    assert config == before
    config["legend_labels"]["A"] = "edited"
    assert spec.legend_labels["A"] == "Same"


@pytest.mark.parametrize("value", ["Shown", "{{label}}", None, 1])
def test_key_admission_rejects_retired_style_name_without_interpreting_value(value: Any) -> None:
    with pytest.raises(ValueError, match="Use legend_labels"):
        validate_plot_config_keys({"series_styles": {"raw": {"name": value}}})


def test_key_admission_preserves_templates_and_unrelated_plugin_style_fields() -> None:
    validate_plot_config_keys({"series_styles": "{{styles}}", "legend_labels": "{{labels}}"})
    config = {
        "legend_labels": {"raw": "{{label}}"},
        "series_styles": {"raw": {"plugin_option": {"name": "Plugin-owned"}}},
    }
    before = deepcopy(config)
    validate_plot_config_keys(config)
    validate_plot_config_values(config)
    assert config == before
