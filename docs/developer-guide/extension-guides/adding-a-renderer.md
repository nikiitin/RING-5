---
title: "Adding a New Rendering Engine"
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 3
---

# Adding a New Rendering Engine

## Overview

RING-5 Unified Engine v2 uses a **dual rendering architecture**.
Every visualization is described by a single, engine-agnostic `FigureConfig`
dataclass (`src/core/models/visualization/figure_config.py`). Two **connectors**
translate that spec into library-specific API calls:

| Connector | Target library | Entry point |
|---|---|---|
| `FigureSpecToPlotly` | Plotly `go.Figure` | `plotly_connector.py` |
| `FigureSpecToMatplotlib` | matplotlib `Axes` | `matplotlib_connector.py` |

The active engine is tracked by `EngineManager`, which stores a
`Literal["plotly", "matplotlib"]` value in Streamlit session state.

**When to add a new engine.** Add a third connector when you need to target a
rendering library that is fundamentally different from Plotly or matplotlib --
for example Altair/Vega-Lite, Bokeh, or a custom Canvas/WebGL renderer. If you
only need a new *export format* (e.g. EPS), extend the existing connectors
instead.

---

## Step 1: Implement the ConnectorProtocol

Every connector must apply styling operations in the order defined by
`_connector_protocol.STYLING_PIPELINE_ORDER` (16 stages). This guarantees
visual consistency across engines.

Create a new file at `src/web/rendering/<engine>_connector.py`:

```python
"""
<Engine> connector -- translate resolved FigureConfig into <Engine> calls.
"""
from __future__ import annotations
from src.core.models.visualization.figure_config import FigureConfig

class FigureSpecTo<Engine>:
    """Stateless translator: FigureConfig -> <Engine> figure updates."""

    @staticmethod
    def apply(spec: FigureConfig, figure: <NativeFigureType>) -> <NativeFigureType>:
        """Apply the full FigureConfig to a native figure object.

        The spec must be **resolved** (no -1 sentinels) before calling.
        """
        # Pipeline order: see _connector_protocol.STYLING_PIPELINE_ORDER
        FigureSpecTo<Engine>._apply_backgrounds(spec, figure)
        FigureSpecTo<Engine>._apply_font_family(spec, figure)
        FigureSpecTo<Engine>._apply_color_palette(spec, figure)
        FigureSpecTo<Engine>._apply_title(spec, figure)
        FigureSpecTo<Engine>._apply_axis_labels(spec, figure)
        FigureSpecTo<Engine>._apply_axis_ticks(spec, figure)
        FigureSpecTo<Engine>._apply_axis_ranges(spec, figure)
        FigureSpecTo<Engine>._apply_axis_colors(spec, figure)
        FigureSpecTo<Engine>._apply_grids(spec, figure)
        FigureSpecTo<Engine>._apply_legends(spec, figure)
        FigureSpecTo<Engine>._apply_reference_lines(spec, figure)
        FigureSpecTo<Engine>._apply_data_labels(spec, figure)
        FigureSpecTo<Engine>._apply_annotations(spec, figure)
        FigureSpecTo<Engine>._apply_separators(spec, figure)
        FigureSpecTo<Engine>._apply_hatching(spec, figure)
        FigureSpecTo<Engine>._apply_margins(spec, figure)
        return figure
```

Each `_apply_*` method is a `@staticmethod` that reads from `FigureConfig`
sub-specs (`spec.axes`, `spec.typography`, `spec.legends`, etc.) and mutates
the native figure object. The connector must be **stateless** -- all context
comes from the spec.

---

## Step 2: Implement Trace Rendering

Trace data lives in engine-agnostic `TraceConfig` subclasses:
`BarTraceConfig`, `LineTraceConfig`, `ScatterTraceConfig`,
`HistogramTraceConfig`, and `HeatmapTraceConfig`
(defined in `src/core/models/visualization/trace_config.py`).

Create a trace renderer at `src/web/rendering/<engine>_trace_renderer.py`
following the pattern of `MatplotlibTraceRenderer`:

```python
class <Engine>TraceRenderer:
    """Draw TraceConfig instances on a native <Engine> canvas."""

    @staticmethod
    def render(
        traces: Sequence[TraceConfig],
        figure: <NativeFigureType>,
        barmode: str = "group",
        palette_colors: Sequence[str] | None = None,
    ) -> <RenderResultType>:
        for idx, trace in enumerate(traces):
            if isinstance(trace, BarTraceConfig):
                ...
            elif isinstance(trace, LineTraceConfig):
                ...
            elif isinstance(trace, ScatterTraceConfig):
                ...
            elif isinstance(trace, HistogramTraceConfig):
                ...
            elif isinstance(trace, HeatmapTraceConfig):
                ...
```

Key rules:
- The trace renderer draws **data only** -- no styling. Layout and style are
  handled by the connector's `apply()` method.
- Handle `yaxis="y2"` traces by creating a secondary axis.
- Respect `palette_colors` overrides when provided.

---

## Step 3: Register with EngineManager

The `EngineManager` class (`src/web/rendering/engine_manager.py`) controls
which engine is active. To add your engine:

1. **Extend `EngineMode`** -- add your engine name to the `Literal` type and
   the `_VALID_MODES` frozenset:

```python
EngineMode = Literal["plotly", "matplotlib", "<engine>"]
_VALID_MODES: frozenset[str] = frozenset({"plotly", "matplotlib", "<engine>"})
```

2. **Add a convenience predicate**:

```python
@staticmethod
def is_<engine>() -> bool:
    return EngineManager.get_engine() == "<engine>"
```

3. **Export from the package** -- update `src/web/rendering/__init__.py`:

```python
from src.web.rendering.<engine>_connector import FigureSpecTo<Engine>
from src.web.rendering.<engine>_trace_renderer import <Engine>TraceRenderer

__all__ = [
    ...,
    "FigureSpecTo<Engine>",
    "<Engine>TraceRenderer",
]
```

4. **Wire into rendering call sites** -- search for `EngineManager.is_plotly()`
   / `is_matplotlib()` guards in the web layer and add an `elif` branch for
   your engine.

---

## Step 4: Add Export Format Support

If your engine supports export formats not already covered (PDF, PNG, SVG,
PGF), extend the export layer:

1. Add the new format string to the export layer in
   `src/web/rendering/figure_export.py` if you introduce a new format.
2. Add a download handler that calls your engine's native export API.
3. Your connector should read the same `FigureConfig` fields (DPI, dimensions,
   font family) that the existing connectors use.

---

## Step 5: Add Tests

Follow the testing patterns in `tests/unit/core/visualization/test_connectors.py`.

### Unit tests for the connector

Test each `_apply_*` method in isolation:

```python
class TestFigureSpecTo<Engine>:

    def _make_simple_fig(self) -> <NativeFigureType>:
        """Create a minimal figure for testing."""
        ...

    def test_apply_backgrounds(self) -> None:
        spec = FigureConfig(
            paper_bgcolor="#F0F0F0",
            plot_bgcolor="#FFFFFF",
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()
        FigureSpecTo<Engine>.apply(resolved, fig)
        # Assert backgrounds were applied to the native figure.

    def test_apply_title(self) -> None:
        spec = FigureConfig(
            title="My Plot",
            typography=TypographyConfig(font_size_title=16),
        )
        resolved = resolve_config(spec)
        fig = self._make_simple_fig()
        FigureSpecTo<Engine>.apply(resolved, fig)
        # Assert title text and font size on the native figure.
```

### Unit tests for the trace renderer

```python
class Test<Engine>TraceRenderer:

    def test_bar_trace(self) -> None:
        traces = [BarTraceConfig(x=["A", "B"], y=[1, 2], name="t")]
        result = <Engine>TraceRenderer.render(traces, fig)
        assert result.trace_count == 1
```

### Integration tests

Add a test to `tests/integration/` that runs the full pipeline:
`TraceBuildResult` -> trace renderer -> connector `apply()` -> native figure.

---

## ConnectorProtocol Method Reference

The 16 styling stages defined in
`src/web/rendering/_connector_protocol.STYLING_PIPELINE_ORDER` and the
`FigureConfig` fields each stage reads:

| # | Stage | FigureConfig fields | Purpose |
|---|---|---|---|
| 1 | `backgrounds` | `paper_bgcolor`, `plot_bgcolor` | Figure and plot area fill |
| 2 | `font_family` | `font_family` | Global typeface |
| 3 | `color_palette` | `color_palette` | Trace color cycle |
| 4 | `title` | `title`, `typography.font_size_title` | Figure title |
| 5 | `axis_labels` | `axes.x.label`, `axes.y.label`, `typography.font_size_*label` | Axis titles |
| 6 | `axis_ticks` | `axes.*.tick_angle`, `axes.*.tick_pad`, `typography.font_size_ticks` | Tick labels and rotation |
| 7 | `axis_ranges` | `axes.*.range`, `axes.*.scale` | Limits and log/linear scale |
| 8 | `axis_colors` | `axes.*.tick_font_color`, `axes.*.axis_line_color` | Tick and spine colors |
| 9 | `grids` | `axes.*.show_grid`, `axes.*.grid_color`, `axes.*.grid_width` | Grid lines |
| 10 | `legends` | `legends[*]` (font, position, orientation, spacing) | Legend rendering |
| 11 | `reference_lines` | `reference_lines[*]` | Horizontal/vertical guide lines |
| 12 | `data_labels` | `data_labels` (`DataLabelConfig`) | Value annotations on bars |
| 13 | `annotations` | `annotations[*]` (`AnnotationConfig`) | Free-form text annotations |
| 14 | `separators` | `separator` (`SeparatorConfig`) | Vertical group dividers |
| 15 | `hatching` | `enable_stripes`, `hatching_sequence` | Bar fill patterns |
| 16 | `margins` | `dimensions.margins` | Figure margins |

Connectors may add engine-specific stages (e.g. `_apply_hovermode` for Plotly,
`_apply_colorbar` for matplotlib). These run alongside the 16 shared stages but
are not part of the protocol.

---

## Checklist

Before merging a new rendering engine, verify:

- [ ] Connector class implements all 16 `STYLING_PIPELINE_ORDER` stages.
- [ ] Connector is **stateless** -- all methods are `@staticmethod`.
- [ ] Trace renderer handles all five `TraceConfig` subclasses (bar, line,
      scatter, histogram, heatmap).
- [ ] `EngineMode` literal and `_VALID_MODES` updated in `engine_manager.py`.
- [ ] Convenience predicate `is_<engine>()` added to `EngineManager`.
- [ ] New classes exported from `src/web/rendering/__init__.py`.
- [ ] Rendering call sites in the web layer updated with new engine branch.
- [ ] Unit tests for each `_apply_*` method (see `test_connectors.py`).
- [ ] Unit tests for the trace renderer (see `test_matplotlib_trace_renderer.py`).
- [ ] Integration test for the end-to-end pipeline.
- [ ] Export formats wired up (if applicable).
- [ ] FigureConfig resolved via `resolve_config()` before passing to connector.
- [ ] No Plotly or matplotlib imports inside the new connector (keep engine
      dependencies isolated).

---

## See Also

- `src/web/rendering/_connector_protocol.py` -- canonical pipeline order.
- `src/web/rendering/plotly_connector.py` -- reference Plotly implementation.
- `src/web/rendering/matplotlib_connector.py` -- reference matplotlib implementation.
- `src/web/rendering/engine_manager.py` -- engine state management.
- `src/web/rendering/matplotlib_trace_renderer.py` -- trace drawing reference.
- `src/core/models/visualization/figure_config.py` -- engine-agnostic spec.
- `src/core/services/visualization/config_resolver.py` -- sentinel resolution.
- `tests/unit/core/visualization/test_connectors.py` -- connector test suite.
