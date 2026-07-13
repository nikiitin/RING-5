---
title: "Adding a Settings Panel"
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 5
---

# Adding a Settings Panel

## Overview

The plot-styling sidebar uses a **pills navigation** system defined in
`src/web/pages/ui/plotting/settings_pills.py`. Each pill corresponds to a
settings panel that renders Streamlit widgets and returns a `PlotConfig`
dictionary of key-value pairs.

There are currently **7 top-level pills** split into two tiers by
progressive disclosure:

| Tier | Pills |
|------|-------|
| Basic (always visible) | Layout, Typography, Legends |
| Advanced (toggle-gated) | Axes, Data Labels, Colors, Advanced |

Within those pills, **11 settings components** live under
`src/web/components/plotting/settings/`, each following the same contract:
accept a `saved_config`, render widgets, return a `PlotConfig` dict.

Adding a new panel requires four artifacts: a `WidgetSection` definition, a
component class, a `SettingsSection` pill registration, and tests.

---

## Step 1 -- Create the Settings Panel Module

Create a new file under
`src/web/components/plotting/settings/<name>_settings.py`.
Follow the existing component pattern -- a class with `__init__(plot_id, plot_type)`
and a `render(saved_config) -> PlotConfig` method.

```python
# src/web/components/plotting/settings/watermark_settings.py
"""Watermark settings component -- overlay text configuration."""

import streamlit as st

from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
    select_option,
    toggle,
)
from src.web.models.plot_models import PlotConfig


class WatermarkSettingsComponent:
    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(self, saved_config: PlotConfig) -> PlotConfig:
        ...  # See Step 2
```

## Step 2 -- Define Widgets Using the WidgetDef System

All declarative widget metadata lives in
`src/web/rendering/widgets/widget_def.py`. Define a `WidgetSection` that
lists every control your panel needs. Available widget types:

| Class | Streamlit widget |
|-------|-----------------|
| `NumberWidgetDef` | `st.number_input` |
| `SliderWidgetDef` | `st.slider` |
| `SelectWidgetDef` | `st.selectbox` |
| `CheckboxWidgetDef` | `st.checkbox` |
| `ColorWidgetDef` | `st.color_picker` |
| `TextWidgetDef` | `st.text_input` |

Each widget definition carries a `key` (config dict key and widget-key
suffix), a `label`, a `default`, and optional `spec_path` for FigureConfig
mapping. Add your section at the bottom of `widget_def.py` and append it
to the `ALL_SECTIONS` tuple:

```python
WATERMARK = WidgetSection(
    id="watermark",
    label="Watermark",
    icon="branding_watermark",
    widgets=(
        CheckboxWidgetDef(
            key="watermark_enabled",
            label="Show Watermark",
            default=False,
        ),
        TextWidgetDef(
            key="watermark_text",
            label="Watermark Text",
            default="DRAFT",
        ),
        NumberWidgetDef(
            key="watermark_font_size",
            label="Font Size",
            default=48,
            min_value=12,
            max_value=200,
            step=4,
        ),
        ColorWidgetDef(
            key="watermark_color",
            label="Color",
            default="#cccccc",
        ),
        SliderWidgetDef(
            key="watermark_opacity",
            label="Opacity",
            default=0.3,
            min_value=0.0,
            max_value=1.0,
            step=0.05,
        ),
    ),
)

ALL_SECTIONS: tuple[WidgetSection, ...] = (
    *STANDARD_SECTIONS,
    ...,
    WATERMARK,          # <-- append here
)
```

## Step 3 -- Map Widget Values to FigureConfig Fields

Inside your component's `render()` method use the `widget_factory` helpers
to read from `saved_config` and collect user input:

```python
def render(self, saved_config: PlotConfig) -> PlotConfig:
    st.markdown("#### Watermark")

    enabled = toggle(
        "Show Watermark", saved_config, "watermark_enabled", self.plot_id
    )
    text = st.text_input(
        "Watermark Text",
        value=saved_config.get("watermark_text", "DRAFT"),
        key=f"watermark_text_{self.plot_id}",
    )
    font_size = numeric_input(
        "Font Size", saved_config, "watermark_font_size", self.plot_id,
        default=48, min_value=12, max_value=200, step=4,
    )
    color = color_picker(
        "Color", saved_config, "watermark_color", self.plot_id,
        default="#cccccc",
    )

    return {
        "watermark_enabled": enabled,
        "watermark_text": text,
        "watermark_font_size": font_size,
        "watermark_color": color,
    }
```

Every key returned here must eventually appear in the `PlotDisplayConfig`
TypedDict (`src/web/models/plot_models.py`) so that downstream applicators
and the config-spec builder can consume them.

## Step 4 -- Register the Panel in the Navigation

Three files need a one-line addition each:

**4a. `settings_pills.py` -- add a `SettingsSection`**

```python
SETTINGS_SECTIONS: list[SettingsSection] = [
    ...
    SettingsSection("watermark", "Watermark", "branding_watermark", advanced=True),
]
```

Set `advanced=True` to keep the pill behind the progressive-disclosure
toggle, or omit it to make the pill always visible.

**4b. `plot_config_ui.py` -- add routing in `render_settings_section()`**

```python
if section == "watermark":
    return WatermarkSettingsComponent(self.plot_id, self.plot_type).render(
        saved_config
    )
```

**4c. `settings/__init__.py` -- re-export the component**

```python
from src.web.components.plotting.settings.watermark_settings import (  # noqa: F401
    WatermarkSettingsComponent,
)
```

## Step 5 -- Add Tests

Create `tests/ui_unit/test_watermark_settings.py`. Follow the established
pattern: mock `st` via `unittest.mock.patch`, verify the returned dict
contains expected keys, and assert default values.

```python
"""Tests for watermark_settings component."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_st():
    with patch("src.web.components.plotting.settings.watermark_settings.st") as m:
        m.checkbox.return_value = False
        m.text_input.return_value = "DRAFT"
        m.color_picker.return_value = "#cccccc"
        m.number_input.return_value = 48
        yield m


class TestWatermarkSettingsComponent:
    def _make(self):
        from src.web.components.plotting.settings.watermark_settings import (
            WatermarkSettingsComponent,
        )
        return WatermarkSettingsComponent(plot_id=1, plot_type="bar")

    def test_returns_expected_keys(self, mock_st):
        result = self._make().render(saved_config={})
        assert "watermark_enabled" in result
        assert "watermark_text" in result
        assert "watermark_font_size" in result
        assert "watermark_color" in result

    def test_defaults(self, mock_st):
        result = self._make().render(saved_config={})
        assert result["watermark_enabled"] is False
        assert result["watermark_text"] == "DRAFT"
```

Also update `tests/unit/test_settings_pills.py`:

- Increment the total-count assertion to account for the new section.
- Add the new key to the `test_advanced_sections` expected list.

---

## Complete Example

The full file set for a hypothetical "Watermark" panel:

| File | Purpose |
|------|---------|
| `src/web/rendering/widgets/widget_def.py` | `WATERMARK` WidgetSection added, appended to `ALL_SECTIONS` |
| `src/web/components/plotting/settings/watermark_settings.py` | `WatermarkSettingsComponent` class |
| `src/web/components/plotting/settings/__init__.py` | Re-export added |
| `src/web/pages/ui/plotting/settings_pills.py` | `SettingsSection` entry added to `SETTINGS_SECTIONS` |
| `src/web/pages/ui/plotting/plot_config_ui.py` | Routing branch in `render_settings_section()` |
| `src/web/models/plot_models.py` | New keys added to `PlotDisplayConfig` |
| `tests/ui_unit/test_watermark_settings.py` | Component unit tests |
| `tests/unit/test_settings_pills.py` | Updated count and key assertions |

---

## Checklist

- [ ] `WidgetSection` created in `widget_def.py` with unique `id` and `key` values
- [ ] Component class created under `settings/` with `render() -> PlotConfig`
- [ ] Component re-exported from `settings/__init__.py`
- [ ] `SettingsSection` added to `SETTINGS_SECTIONS` in `settings_pills.py`
- [ ] Routing branch added in `PlotConfigUIMixin.render_settings_section()`
- [ ] New config keys added to `PlotDisplayConfig` TypedDict
- [ ] Unit tests pass: `pytest tests/ui_unit/test_<name>_settings.py`
- [ ] Existing pills tests updated and passing: `pytest tests/unit/test_settings_pills.py`
- [ ] Widget keys use `self.plot_id` suffix to avoid collisions in multi-plot pages

## See Also

- `src/web/rendering/widgets/widget_def.py` -- all `WidgetDef` subclasses and `WidgetSection`
- `src/web/components/plotting/settings/widget_factory.py` -- Streamlit widget helpers (`select_option`, `numeric_input`, `color_picker`, `toggle`, `slider`)
- `src/web/pages/ui/plotting/settings_pills.py` -- pills navigation and `SettingsSection` dataclass
- `src/web/pages/ui/plotting/plot_config_ui.py` -- `PlotConfigUIMixin.render_settings_section()` dispatcher
- `src/web/models/plot_models.py` -- `PlotConfig` alias and `PlotDisplayConfig` TypedDict
