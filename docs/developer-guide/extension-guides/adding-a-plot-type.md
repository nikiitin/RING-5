# Adding a New Plot Type

## Overview

The RING-5 Unified Engine v2 plotting system follows the **Factory + ABC** pattern.
Every plot type is a concrete subclass of `BasePlot` and is registered with
`PlotFactory` so that the rest of the application -- lifecycle management,
serialization, rendering, and export -- works automatically.

You should add a new plot type when:

- The built-in types (bar, line, scatter, heatmap, histogram, grouped bar,
  stacked bar, grouped stacked bar, dual-axis bar dot) do not represent the
  visual encoding you need.
- The new visualization requires a different trace structure or data-to-visual
  mapping than an existing type can provide.

The typical new-plot-type implementation touches 3 to 5 files, depending on
whether you need a custom trace config or style UI strategy. The sections below
walk through each step in order.

---

## Step 1: Create the Plot Class

Create a new file under `src/web/pages/ui/plotting/types/`. The file should
contain a single class that extends `BasePlot`.

```python
# src/web/pages/ui/plotting/types/waterfall_plot.py
"""Waterfall plot implementation."""

from typing import override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


class WaterfallPlot(BasePlot):
    """Waterfall chart showing cumulative effect of sequential values."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "waterfall")
```

The third argument to `super().__init__()` is the **type identifier** string.
It must match the key you will use when registering with `PlotFactory`.
Use `snake_case` for plot type identifiers (e.g., `"waterfall"`,
`"grouped_bar"`).

The constructor must accept exactly `(plot_id: int, name: str)` because
`PlotFactory.create_plot()` calls `plot_constructor(plot_id, name)`.

---

## Step 2: Implement Required Abstract Methods

`BasePlot` declares three abstract methods. Every plot type must override all
three.

### 2a. `render_config_ui`

Renders the Streamlit widgets that let the user configure which columns map to
X, Y, color, and any plot-specific parameters. Return a `PlotConfig` dict.

For standard X/Y/color selection, reuse the helpers in
`src/web/components/plotting/config/base_plot_config.py`:

```python
from src.web.components.plotting.config.base_plot_config import (
    render_common_with_color,
)

@override
def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
    return render_common_with_color(data, saved_config, self.plot_id)
```

If your plot needs different or additional widgets (for example a "measure"
column for waterfall), build a custom layout using `render_common_config` as
a starting point and add your own `st.selectbox` / `st.checkbox` calls.

### 2b. `create_traces`

This is the core data-to-visual mapping. It receives the processed DataFrame
and the config dict, and must return a `TraceBuildResult` containing a list of
engine-agnostic `TraceConfig` objects.

```python
from src.core.models.visualization.trace_config import BarTraceConfig

@override
def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
    x_col: str = config["x"]
    y_col: str = config["y"]
    measure_col: str | None = config.get("measure")

    traces = []
    # ... build one or more TraceConfig (or subclass) instances ...
    traces.append(
        BarTraceConfig(
            name=y_col,
            x=data[x_col].tolist(),
            y=data[y_col].tolist(),
        )
    )
    return TraceBuildResult(traces=traces)
```

Key guidelines for `create_traces`:

- Always work on a **copy** of the DataFrame if you modify it (`data = data.copy()`).
- Use the shared `build_color_grouped_traces` helper from
  `src/web/pages/ui/plotting/types/_trace_helpers.py` when your plot supports
  a color-by column.
- Return `TraceBuildResult` with appropriate metadata: set `barmode` for bar
  variants, `secondary_y` for dual-axis, `custom_x_ticks` for manual tick
  labels, and `shapes`/`annotations` for separators or group labels.

### 2c. `get_legend_column`

Returns the name of the DataFrame column that drives legend grouping, or `None`
if the plot has no legend split.

```python
@override
def get_legend_column(self, config: PlotConfig) -> str | None:
    result = config.get("color")
    return str(result) if result is not None else None
```

---

## Step 3: Register with PlotFactory

Registration makes your plot type available to the entire application -- the
plot creation UI, serialization/deserialization, and portfolio save/load all
rely on `PlotFactory`.

### 3a. Export from the types package

Add your class to the types package `__init__.py`:

```python
# src/web/pages/ui/plotting/types/__init__.py
from .waterfall_plot import WaterfallPlot

__all__ = [
    # ... existing entries ...
    "WaterfallPlot",
]
```

### 3b. Register in the factory

In `src/web/pages/ui/plotting/plot_factory.py`, import and add your class to
both `_plot_classes` and `_plot_metadata`:

```python
from .types import WaterfallPlot

# Inside PlotFactory:
_plot_classes: dict[str, Callable[[int, str], BasePlot]] = {
    # ... existing entries ...
    "waterfall": WaterfallPlot,
}

_plot_metadata: dict[str, PlotTypeMetadata] = {
    # ... existing entries ...
    "waterfall": {
        "display_name": "Waterfall Chart",
        "icon": "waterfall_chart",
        "category": "comparison",
    },
}
```

Alternatively, you can register at runtime (useful for plugins or tests):

```python
PlotFactory.register_plot_type(
    "waterfall",
    WaterfallPlot,
    metadata={"display_name": "Waterfall Chart", "icon": "waterfall_chart", "category": "comparison"},
)
```

The `PlotTypeMetadata` TypedDict requires three fields:

| Field          | Type  | Purpose                                             |
|----------------|-------|-----------------------------------------------------|
| `display_name` | `str` | Human-readable label shown in the UI                |
| `icon`         | `str` | Material icon name for the plot type selector       |
| `category`     | `str` | Grouping key: `"basic"`, `"comparison"`, or `"distribution"` |

---

## Step 4: Create a Plot-Specific Config Component (Optional)

If the standard X/Y/color selectors are not sufficient, create a dedicated
config component under `src/web/components/plotting/config/`. This component
renders the Streamlit widgets for your plot-specific parameters.

```python
# src/web/components/plotting/config/waterfall_config.py
import streamlit as st
import pandas as pd

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_common_config,
)
from src.web.models.plot_models import PlotConfig


def render_waterfall_config(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    config = render_common_config(data, saved_config, plot_id)
    _, categorical_cols = detect_column_types(data)

    measure_options = [None] + categorical_cols
    measure = st.selectbox(
        "Measure column (relative/total)",
        options=measure_options,
        key=f"measure_{plot_id}",
    )
    config["measure"] = measure
    return config
```

Then call it from your plot class:

```python
@override
def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
    from src.web.components.plotting.config.waterfall_config import render_waterfall_config
    return render_waterfall_config(data, saved_config, self.plot_id)
```

---

## Step 5: Create a Style UI Strategy (Optional)

The `StyleUIFactory` selects a style UI strategy for per-series visual options
(colors, line styles, marker symbols, etc.). If your new plot type needs
unique style controls, extend `BaseStyleUI`:

```python
# src/web/pages/ui/plotting/styles/waterfall_ui.py
from src.web.pages.ui.plotting.styles.base_ui import BaseStyleUI

class WaterfallStyleUI(BaseStyleUI):
    def _render_specific_series_visuals(self, saved_config, series_name, key_prefix):
        # Render waterfall-specific series options (connector line style, etc.)
        ...
```

Then add a dispatch branch in `StyleUIFactory.get_strategy()` in
`src/web/pages/ui/plotting/styles/factory.py`:

```python
class StyleUIFactory:
    @staticmethod
    def get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI:
        if plot_type == "waterfall":
            return WaterfallStyleUI(plot_id, plot_type)
        # ... existing branches ...
```

If your plot type does not need custom series styling, the default
`BaseStyleUI` is used automatically via the `else` branch.

---

## Step 6: Add Tests

Follow the testing patterns established in the existing test suite. At minimum,
write the following:

### Unit test: trace creation

```python
# tests/unit/test_waterfall_plot.py
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.waterfall_plot import WaterfallPlot


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame({
        "Category": ["Revenue", "COGS", "OpEx", "Tax", "Net"],
        "Amount": [100, -40, -30, -10, 20],
    })


class TestWaterfallPlot:
    def test_create_figure_returns_figure(self, sample_data: pd.DataFrame) -> None:
        plot = WaterfallPlot(1, "Test Waterfall")
        config = {"x": "Category", "y": "Amount"}
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_create_traces_returns_traces(self, sample_data: pd.DataFrame) -> None:
        plot = WaterfallPlot(1, "Test Waterfall")
        config = {"x": "Category", "y": "Amount"}
        result = plot.create_traces(sample_data, config)
        assert len(result.traces) >= 1

    def test_get_legend_column_with_color(self) -> None:
        plot = WaterfallPlot(1, "Test")
        assert plot.get_legend_column({"color": "Region"}) == "Region"

    def test_get_legend_column_without_color(self) -> None:
        plot = WaterfallPlot(1, "Test")
        assert plot.get_legend_column({}) is None
```

### Factory registration test

Add your type to the expected set in `tests/unit/test_plot_factory.py`:

```python
EXPECTED_PLOT_TYPES = {
    # ... existing types ...
    "waterfall",
}
```

### Serialization round-trip test

Verify `to_dict()` and `from_dict()` work correctly:

```python
def test_serialization_round_trip(self, sample_data: pd.DataFrame) -> None:
    plot = WaterfallPlot(1, "Round Trip")
    plot.config = {"x": "Category", "y": "Amount"}
    plot.processed_data = sample_data

    data = plot.to_dict()
    restored = WaterfallPlot.from_dict(data)

    assert restored.plot_type == "waterfall"
    assert restored.config == plot.config
    assert restored.processed_data is not None
```

---

## Complete Example

Below is a complete skeleton for a hypothetical "waterfall" plot type. It reuses
`BarTraceConfig` since waterfall charts are typically rendered as bars with
cumulative offsets.

```python
# src/web/pages/ui/plotting/types/waterfall_plot.py
"""Waterfall plot implementation."""

from typing import override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config.base_plot_config import (
    render_common_with_color,
)
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


class WaterfallPlot(BasePlot):
    """Waterfall chart showing cumulative effect of sequential values."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "waterfall")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for waterfall plot."""
        return render_common_with_color(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce waterfall bar traces with cumulative offset computation."""
        x_col: str = config["x"]
        y_col: str = config["y"]

        data = data.copy()
        values = data[y_col].tolist()
        categories = data[x_col].astype(str).tolist()

        # Compute cumulative bases for the waterfall effect
        bases: list[float] = []
        cumulative: float = 0.0
        for v in values:
            bases.append(cumulative)
            cumulative += v

        traces = [
            BarTraceConfig(
                name=y_col,
                x=categories,
                y=values,
            ),
        ]

        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for waterfall plot."""
        result = config.get("color")
        return str(result) if result is not None else None
```

---

## Checklist

Before submitting your new plot type, verify the following:

- [ ] Class extends `BasePlot` and passes the type identifier string to `super().__init__()`.
- [ ] Constructor signature is `(self, plot_id: int, name: str)`.
- [ ] All three abstract methods are implemented: `render_config_ui`, `create_traces`, `get_legend_column`.
- [ ] All overridden methods use the `@override` decorator.
- [ ] `create_traces` returns a `TraceBuildResult` with at least one `TraceConfig` subclass instance.
- [ ] `create_traces` does not mutate the input DataFrame (make a copy first).
- [ ] Class is exported from `src/web/pages/ui/plotting/types/__init__.py`.
- [ ] Class is registered in `PlotFactory._plot_classes` with a `snake_case` key.
- [ ] `PlotTypeMetadata` is provided in `PlotFactory._plot_metadata` with `display_name`, `icon`, and `category`.
- [ ] Unit tests cover trace creation, legend column, and serialization round-trip.
- [ ] The factory test in `tests/unit/test_plot_factory.py` is updated to include the new type.
- [ ] If a custom `TraceConfig` subclass was needed, it is added to `src/core/models/visualization/trace_config.py` and a converter is added to `src/web/rendering/trace_to_plotly.py`.
- [ ] If a custom style UI is needed, it extends `BaseStyleUI` and the `StyleUIFactory` is updated.
- [ ] Type annotations are present on all public methods.
- [ ] The `plot_type` literal in `TraceConfig.trace_type` is extended if the new type does not map to an existing trace kind.

---

## See Also

- `src/web/pages/ui/plotting/base_plot.py` -- `BasePlot` ABC with all lifecycle methods.
- `src/web/pages/ui/plotting/plot_factory.py` -- `PlotFactory` registry and `PlotTypeMetadata` schema.
- `src/web/pages/ui/plotting/types/bar_plot.py` -- Minimal reference implementation (69 lines).
- `src/core/models/visualization/trace_config.py` -- Engine-agnostic trace dataclasses.
- `src/core/models/visualization/trace_build_result.py` -- Return type for `create_traces`.
- `src/web/rendering/trace_to_plotly.py` -- Trace-to-Plotly conversion dispatcher.
- `src/web/pages/ui/plotting/styles/factory.py` -- `StyleUIFactory` dispatch logic.
- `src/web/components/plotting/config/base_plot_config.py` -- Shared config UI helpers.
- `src/web/pages/ui/plotting/types/_trace_helpers.py` -- `build_color_grouped_traces` shared helper.
- `tests/unit/test_plot_factory.py` -- Factory registration tests.
- `tests/unit/test_plot_types.py` -- Per-type trace creation tests.
