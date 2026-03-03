# Adding a New Plot Type

## Overview

- Pattern: Factory + ABC
- Base class: `BasePlot` (`src/web/pages/ui/plotting/base_plot.py`)
- Factory: `PlotFactory` (`src/web/pages/ui/plotting/plot_factory.py`)
- Trace models: `src/core/models/visualization/trace_config.py`
- Trace converter: `src/web/rendering/trace_to_plotly.py`
- Reference implementation: `BarPlot` (`src/web/pages/ui/plotting/types/bar_plot.py`)

## Abstract Methods to Implement

```python
# src/web/pages/ui/plotting/base_plot.py

class BasePlot(PlotConfigUIMixin, ABC):

    def __init__(self, plot_id: int, name: str, plot_type: str) -> None:
        self.plot_id: int = plot_id
        self.name: str = name
        self.plot_type: str = plot_type
        self.config: PlotConfig = {}
        self.processed_data: pd.DataFrame | None = None
        self.last_generated_fig: go.Figure | None = None
        self.last_traces: TraceBuildResult | None = None
        self.pipeline: list[PipelineStep] = []
        self.pipeline_counter: int = 0
        self.legend_mappings_by_column: dict[str, dict[str, str]] = {}
        self.legend_mappings: dict[str, str] = {}
        self._style_ui = StyleUIFactory.get_strategy(self.plot_id, self.plot_type)
        self._applicator = StyleApplicator(self.plot_type)

    @abstractmethod
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce engine-agnostic trace data from data and config."""

    @abstractmethod
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get the column name used for legend/color coding."""

    # Inherited from PlotConfigUIMixin:
    @abstractmethod
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render Streamlit widgets for plot-type-specific configuration."""
```

| Method | Purpose |
|--------|---------|
| `create_traces` | Convert DataFrame + config into `TraceBuildResult` (list of `TraceConfig`) |
| `get_legend_column` | Return column name driving legend grouping (or None) |
| `render_config_ui` | Render Streamlit widgets for X/Y/color selection |

## Concrete Methods Provided by BasePlot

| Method | Purpose |
|--------|---------|
| `create_figure(data, config)` | Calls `create_traces` then `traces_to_plotly` |
| `generate_figure()` | Full pipeline: create + style + legend labels |
| `apply_common_layout(fig, config)` | Delegates to `StyleApplicator` |
| `to_dict()` / `from_dict(data)` | Serialization for portfolio save/load |
| `update_from_relayout(relayout_data)` | Handles zoom/pan events |

## Steps

### 1. Create the plot class file

```python
# src/web/pages/ui/plotting/types/violin_plot.py

from typing import override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import TraceConfig
from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_common_with_color,
)
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


class ViolinPlot(BasePlot):
    """Violin plot type."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "violin")

    @override
    def render_config_ui(
        self, data: pd.DataFrame, saved_config: PlotConfig
    ) -> PlotConfig:
        return render_common_with_color(data, saved_config, self.plot_id)

    @override
    def create_traces(
        self, data: pd.DataFrame, config: PlotConfig
    ) -> TraceBuildResult:
        x_col: str = config["x"]
        y_col: str = config["y"]
        # Build trace configs (engine-agnostic)
        traces = [
            TraceConfig(
                name=y_col,
                trace_type="bar",  # fallback; see step 2 for custom type
                x=data[x_col].tolist(),
                y=data[y_col].tolist(),
            )
        ]
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        result = config.get("color")
        return str(result) if result is not None else None
```

### 2. (Optional) Create a custom TraceConfig subclass

```python
# src/core/models/visualization/trace_config.py  (add to existing file)

@dataclass
class ViolinTraceConfig(TraceConfig):
    """Violin-specific trace parameters."""
    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "bar"
    side: str = "both"         # "both", "positive", "negative"
    meanline: bool = True
    bandwidth: float | None = None
```

### 3. Add converter in trace_to_plotly.py

```python
# src/web/rendering/trace_to_plotly.py

# In _convert_trace() dispatcher, add before the else branch:
elif isinstance(trace, ViolinTraceConfig):
    return _violin_trace(trace)

# New converter function:
def _violin_trace(trace: ViolinTraceConfig) -> go.Violin:
    kwargs: dict[str, Any] = {
        "x": trace.x,
        "y": trace.y,
        "name": trace.name,
        "side": trace.side,
        "meanline_visible": trace.meanline,
        "opacity": trace.opacity,
        "showlegend": trace.show_in_legend,
    }
    if trace.color:
        kwargs["marker"] = {"color": trace.color}
    if trace.bandwidth:
        kwargs["bandwidth"] = trace.bandwidth
    return go.Violin(**{k: v for k, v in kwargs.items() if v is not None})
```

### 4. Export from the types package

```python
# src/web/pages/ui/plotting/types/__init__.py  (add to existing imports)

from src.web.pages.ui.plotting.types.violin_plot import ViolinPlot
```

### 5. Register with PlotFactory

```python
# src/web/pages/ui/plotting/plot_factory.py

# Add to _plot_classes dict:
"violin": ViolinPlot,

# Add to _plot_metadata dict:
"violin": {
    "display_name": "Violin Plot",
    "icon": "music_note",
    "category": "distribution",
},
```

Or register at runtime:

```python
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.types.violin_plot import ViolinPlot

PlotFactory.register_plot_type(
    "violin",
    ViolinPlot,
    metadata={"display_name": "Violin Plot", "icon": "music_note", "category": "distribution"},
)
```

### 6. (Optional) Add custom style UI strategy

```python
# src/web/pages/ui/plotting/styles/factory.py

# Add branch in StyleUIFactory.get_strategy():
elif "violin" in plot_type:
    return BaseStyleUI(plot_id, plot_type)
```

## PlotFactory API Reference

| Method | Returns |
|--------|---------|
| `PlotFactory.create_plot(plot_type, plot_id, name)` | `BasePlot` instance |
| `PlotFactory.register_plot_type(type, cls, metadata)` | None (validates BasePlot subclass) |
| `PlotFactory.get_available_plot_types()` | `list[str]` |
| `PlotFactory.get_plot_metadata()` | `dict[str, PlotTypeMetadata]` |

## PlotTypeMetadata Schema

```python
class PlotTypeMetadata(TypedDict):
    display_name: str   # "Violin Plot"
    icon: str           # Material icon name: "music_note"
    category: str       # "basic", "comparison", or "distribution"
```

## Existing Plot Types

| Type ID | Class | Category |
|---------|-------|----------|
| `bar` | `BarPlot` | basic |
| `line` | `LinePlot` | basic |
| `scatter` | `ScatterPlot` | basic |
| `grouped_bar` | `GroupedBarPlot` | comparison |
| `stacked_bar` | `StackedBarPlot` | comparison |
| `grouped_stacked_bar` | `GroupedStackedBarPlot` | comparison |
| `dual_axis_bar_dot` | `DualAxisBarDotPlot` | comparison |
| `heatmap` | `HeatmapPlot` | distribution |
| `histogram` | `HistogramPlot` | distribution |

## Conventions

1. Plot type IDs: `snake_case` (`grouped_bar`, `dual_axis_bar_dot`)
2. Constructor signature: `__init__(self, plot_id: int, name: str)`
3. Pass `plot_type` string to `super().__init__` as third argument
4. Use `@override` decorator on all overridden methods
5. Return new DataFrames from `create_traces` (no mutation of input)
6. Layer rule: `BasePlot` lives in `src/web/`, trace configs in `src/core/`
