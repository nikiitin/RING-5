---
title: "Adding a Rendering Engine"
parent: Development
grand_parent: Engineering Reference
nav_order: 4
---

# Adding a Rendering Engine

> Scope: implementing a new visualization backend (connector) for the RING-5 figure pipeline.

---

## Key Files

| File | Line(s) | Role |
|------|---------|------|
| `src/web/rendering/_connector_protocol.py` | 12-29 | `STYLING_PIPELINE_ORDER` -- mandatory stage ordering |
| `src/web/rendering/engine_manager.py` | 35-37, 40-84 | `EngineManager` -- engine state in `st.session_state` |
| `src/web/rendering/plotly_connector.py` | 40-77 | `FigureSpecToPlotly` -- reference Plotly connector |
| `src/web/rendering/matplotlib_connector.py` | 48-84 | `FigureSpecToMatplotlib` -- reference Matplotlib connector |
| `src/web/rendering/trace_to_plotly.py` | 1-30 | `traces_to_plotly()` -- TraceBuildResult to go.Figure |
| `src/core/models/visualization/figure_config.py` | -- | `FigureConfig` dataclass -- resolved spec input |

---

## Architecture Overview

```
+------------------+     +------------------+     +---------------------+
| BasePlot         |     | StyleApplicator  |     | ConfigSpecBuilder   |
| .create_traces() |---->| .apply_styles()  |---->| .build()            |
| -> TraceBuildResult     |                  |     | -> FigureConfig     |
+------------------+     +--------+---------+     +----------+----------+
                                  |                           |
                                  v                           v
                         +--------+---------+     +-----------+----------+
                         | EngineManager    |     | resolve_config()     |
                         | .get_engine()    |     | -> resolved spec     |
                         +--------+---------+     +-----------+----------+
                                  |                           |
                    +-------------+-------------+             |
                    |                           |             |
           +-------v--------+         +--------v-------+     |
           | traces_to_     |         | traces_to_     |     |
           | plotly()       |         | <new_engine>() |     |
           | -> go.Figure   |         | -> EngFigure   |     |
           +-------+--------+         +--------+-------+     |
                   |                           |              |
           +-------v--------+         +--------v-------+     |
           | FigureSpecTo   |         | FigureSpecTo   |<----+
           | Plotly.apply() |         | <NewEng>.apply |
           +----------------+         +----------------+
```

---

## STYLING_PIPELINE_ORDER (16 stages)

Every connector MUST apply these stages in this exact order.

Source: `src/web/rendering/_connector_protocol.py:12-29`

| # | Stage | What it controls |
|---|-------|------------------|
| 1 | `backgrounds` | Plot and paper background colors |
| 2 | `font_family` | Global font family |
| 3 | `color_palette` | Trace/series color sequence |
| 4 | `title` | Chart title text, font, position |
| 5 | `axis_labels` | X/Y axis label text and styling |
| 6 | `axis_ticks` | Tick values, rotation, font size |
| 7 | `axis_ranges` | Axis min/max bounds |
| 8 | `axis_colors` | Axis line and tick mark colors |
| 9 | `grids` | Grid line visibility, color, width |
| 10 | `legends` | Legend position, font, border, columns |
| 11 | `reference_lines` | Horizontal/vertical reference lines |
| 12 | `data_labels` | Per-bar / per-point value labels |
| 13 | `annotations` | Free-text annotations |
| 14 | `separators` | Group separator vertical lines |
| 15 | `hatching` | Bar hatch patterns |
| 16 | `margins` | Figure margins / padding |

---

## Step-by-Step: Add a New Rendering Engine

### Step 1 -- Extend EngineMode

File: `src/web/rendering/engine_manager.py`

```python
# Line 35: add new literal value
EngineMode = Literal["plotly", "matplotlib", "bokeh"]

# Line 37: add to valid set
_VALID_MODES: frozenset[str] = frozenset({"plotly", "matplotlib", "bokeh"})
```

### Step 2 -- Create the trace converter

File: `src/web/rendering/trace_to_bokeh.py` (new)

```python
"""Convert engine-agnostic TraceBuildResult to a Bokeh figure."""

from __future__ import annotations

from typing import Any

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    HeatmapTraceConfig,
    HistogramTraceConfig,
)

def traces_to_bokeh(result: TraceBuildResult) -> Any:
    """Convert TraceBuildResult to a Bokeh figure.

    Dispatches each TraceConfig subclass to a type-specific builder.
    """
    from bokeh.plotting import figure

    fig = figure()
    for trace in result.traces:
        if isinstance(trace, BarTraceConfig):
            _add_bar(fig, trace)
        elif isinstance(trace, LineTraceConfig):
            _add_line(fig, trace)
        elif isinstance(trace, ScatterTraceConfig):
            _add_scatter(fig, trace)
        # ... additional trace types
    return fig

def _add_bar(fig: Any, trace: BarTraceConfig) -> None: ...
def _add_line(fig: Any, trace: LineTraceConfig) -> None: ...
def _add_scatter(fig: Any, trace: ScatterTraceConfig) -> None: ...
```

### Step 3 -- Create the styling connector

File: `src/web/rendering/figure_spec_to_bokeh.py` (new)

```python
"""Bokeh connector -- translate resolved FigureConfig into Bokeh updates."""

from __future__ import annotations

from typing import Any

from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering._connector_protocol import STYLING_PIPELINE_ORDER


class FigureSpecToBokeh:
    """Stateless translator: FigureConfig -> Bokeh figure updates.

    The FigureConfig must be **resolved** (no -1 sentinels) before calling.
    """

    @staticmethod
    def apply(spec: FigureConfig, fig: Any) -> Any:
        """Apply the full FigureConfig to a Bokeh figure.

        Stages follow STYLING_PIPELINE_ORDER exactly.
        """
        FigureSpecToBokeh._apply_backgrounds(spec, fig)
        FigureSpecToBokeh._apply_font_family(spec, fig)
        FigureSpecToBokeh._apply_color_palette(spec, fig)
        FigureSpecToBokeh._apply_title(spec, fig)
        FigureSpecToBokeh._apply_axis_labels(spec, fig)
        FigureSpecToBokeh._apply_axis_ticks(spec, fig)
        FigureSpecToBokeh._apply_axis_ranges(spec, fig)
        FigureSpecToBokeh._apply_axis_colors(spec, fig)
        FigureSpecToBokeh._apply_grids(spec, fig)
        FigureSpecToBokeh._apply_legends(spec, fig)
        FigureSpecToBokeh._apply_reference_lines(spec, fig)
        FigureSpecToBokeh._apply_data_labels(spec, fig)
        FigureSpecToBokeh._apply_annotations(spec, fig)
        FigureSpecToBokeh._apply_separators(spec, fig)
        FigureSpecToBokeh._apply_hatching(spec, fig)
        FigureSpecToBokeh._apply_margins(spec, fig)
        return fig

    # -- Individual stage implementations --

    @staticmethod
    def _apply_backgrounds(spec: FigureConfig, fig: Any) -> None:
        """Set plot and paper background from spec.backgrounds."""
        if spec.backgrounds is None:
            return
        # fig.background_fill_color = spec.backgrounds.plot_bgcolor
        ...

    @staticmethod
    def _apply_font_family(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_color_palette(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_title(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_axis_labels(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_axis_ticks(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_axis_ranges(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_axis_colors(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_grids(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_legends(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_reference_lines(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_data_labels(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_annotations(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_separators(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_hatching(spec: FigureConfig, fig: Any) -> None: ...
    @staticmethod
    def _apply_margins(spec: FigureConfig, fig: Any) -> None: ...
```

### Step 4 -- Wire rendering dispatch

Update the page/controller code that checks `EngineManager.get_engine()`:

```python
# In the render path (e.g., controller or page)
from src.web.rendering.engine_manager import EngineManager

engine = EngineManager.get_engine()
if engine == "plotly":
    fig = traces_to_plotly(trace_result)
    fig = FigureSpecToPlotly.apply(resolved_spec, fig)
    st.plotly_chart(fig)
elif engine == "matplotlib":
    # existing matplotlib path
    ...
elif engine == "bokeh":
    fig = traces_to_bokeh(trace_result)
    fig = FigureSpecToBokeh.apply(resolved_spec, fig)
    st.bokeh_chart(fig)
```

### Step 5 -- Add UI toggle

Add the new engine option to the engine toggle widget in the settings UI.

---

## Connector Pattern Rules

| Rule | Detail |
|------|--------|
| Stateless | All methods are `@staticmethod`; no instance state |
| Resolved input | `FigureConfig` must have no `-1` sentinel values |
| Stage ordering | Follow `STYLING_PIPELINE_ORDER` exactly |
| Null-safe | Each `_apply_*` checks `if spec.<field> is None: return` |
| In-place mutation | Connector mutates the figure object and returns it |
| Lazy imports | Import engine library inside methods to avoid missing-dep errors |

---

## Reference: Method Signatures Comparison

| Method | Plotly (`plotly_connector.py:48`) | Matplotlib (`matplotlib_connector.py:58`) |
|--------|----------------------------------|-------------------------------------------|
| `apply()` | `(spec: FigureConfig, fig: go.Figure) -> go.Figure` | `(spec: FigureConfig, ax: Axes, render_result: MatplotlibRenderResult \| None = None) -> None` |
| Return | Returns mutated `fig` | Returns `None` (mutates `ax` in place) |
| Extra args | None | Optional `render_result` for heatmap colorbar |

---

## Checklist for New Engine

- [ ] `EngineMode` literal and `_VALID_MODES` extended in `engine_manager.py`
- [ ] `trace_to_<engine>.py` converts `TraceBuildResult` per trace type
- [ ] `figure_spec_to_<engine>.py` implements all 16 pipeline stages
- [ ] Rendering dispatch updated in controller/page code
- [ ] UI toggle added for engine selection
- [ ] Unit tests: each `_apply_*` method tested in isolation
- [ ] Integration test: full data-to-figure pipeline with new engine
- [ ] `EngineManager.is_<engine>()` convenience method added
