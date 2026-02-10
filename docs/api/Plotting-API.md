---
title: "Plotting API"
nav_order: 24
---

# Plotting API

<!-- markdownlint-disable MD024 -->

Complete API reference for RING-5's plotting system.

## Overview

The plotting system uses the **Factory Pattern** to create plot instances. All plots inherit from `BasePlot` and implement `create_figure()`.

## PlotFactory

### Class: `PlotFactory`

Factory for creating plot instances.

**Location**: `src/plotting/plot_factory.py`

#### Methods

##### `create_plot(plot_type, plot_id, name="Plot")`

Create plot instance by type.

**Parameters**:

- `plot_type` (str): Plot type identifier
- `plot_id` (int): Unique plot ID
- `name` (str): Plot name

**Returns**: `BasePlot` - Plot instance

**Raises**: `ValueError` - If plot type unknown

**Supported Plot Types**:

- `"bar"` - Simple bar chart
- `"grouped_bar"` - Grouped bar chart
- `"stacked_bar"` - Stacked bar chart
- `"grouped_stacked_bar"` - Grouped stacked bar chart
- `"line"` - Line plot
- `"scatter"` - Scatter plot
- `"histogram"` - Histogram plot

**Example**:

```python
from src.plotting.plot_factory import PlotFactory

# Create bar plot
plot = PlotFactory.create_plot("bar", plot_id=1, name="IPC Comparison")

# Configure
plot.config = {
    "x_column": "benchmark",
    "y_column": "ipc",
    "title": "IPC by Benchmark"
}

# Generate figure
import pandas as pd
data = pd.read_csv("data.csv")
fig = plot.create_figure(data)

# Display (Streamlit)
import streamlit as st
st.plotly_chart(fig, use_container_width=True)
```

## BasePlot

### Class: `BasePlot`

Abstract base class for all plots.

**Location**: `src/plotting/base_plot.py`

#### Attributes

- `plot_id` (int): Unique identifier
- `name` (str): Plot name
- `plot_type` (str): Type identifier
- `config` (Dict[str, Any]): Configuration dictionary
- `data_source_id` (int | None): Associated data source

#### Methods

##### `create_figure(data)`

Generate Plotly figure from data (must be implemented by subclasses).

**Parameters**:

- `data` (pd.DataFrame): Input data

**Returns**: `go.Figure` - Plotly figure

**Raises**:

- `KeyError` - Required columns missing
- `ValueError` - Invalid configuration

##### `update_config(new_config)`

Update plot configuration.

**Parameters**:

- `new_config` (Dict[str, Any]): New configuration

**Example**:

```python
plot.update_config({
    "title": "New Title",
    "x_column": "different_column"
})
```

## Plot Types

### BarPlot

Simple bar chart.

**Configuration**:

```python
{
    "x_column": str,      # X-axis data (categories)
    "y_column": str,      # Y-axis data (values)
    "title": str,         # Plot title
    "color": str,         # Bar color
    "show_values": bool,  # Show values on bars
}
```

**Example**:

```python
plot = PlotFactory.create_plot("bar", 1)
plot.config = {
    "x_column": "benchmark",
    "y_column": "ipc",
    "title": "IPC by Benchmark",
    "color": "steelblue",
    "show_values": True
}
fig = plot.create_figure(data)
```

### GroupedBarPlot

Grouped bar chart (multiple bars per category).

**Configuration**:

```python
{
    "x_column": str,      # X-axis (categories)
    "y_column": str,      # Y-axis (values)
    "group_by": str,      # Grouping column
    "title": str,
    "color_map": Dict[str, str],  # Group → color mapping
}
```

**Example**:

```python
plot = PlotFactory.create_plot("grouped_bar", 1)
plot.config = {
    "x_column": "benchmark",
    "y_column": "ipc",
    "group_by": "config",
    "title": "IPC Comparison",
    "color_map": {
        "baseline": "blue",
        "optimized": "green"
    }
}
fig = plot.create_figure(data)
```

### StackedBarPlot

Stacked bar chart (bars stacked vertically).

**Configuration**:

```python
{
    "x_column": str,      # X-axis
    "y_column": str,      # Y-axis (values)
    "stack_by": str,      # Stacking dimension
    "title": str,
    "color_map": Dict[str, str],
}
```

### GroupedStackedBarPlot

Grouped stacked bars (complex multi-dimensional).

**Configuration**:

```python
{
    "x_column": str,
    "y_column": str,
    "group_by": str,      # Primary grouping
    "stack_by": str,      # Secondary stacking
    "title": str,
    "color_map": Dict[str, str],
}
```

### LinePlot

Line plot for time-series or continuous data.

**Configuration**:

```python
{
    "x_column": str,      # X-axis
    "y_column": str,      # Y-axis
    "trace_by": str,      # Optional: separate traces
    "title": str,
    "line_width": int,    # Line thickness
    "show_markers": bool, # Show data points
}
```

**Example**:

```python
plot = PlotFactory.create_plot("line", 1)
plot.config = {
    "x_column": "time",
    "y_column": "ipc",
    "trace_by": "config",
    "title": "IPC Over Time",
    "line_width": 2,
    "show_markers": True
}
fig = plot.create_figure(data)
```

### ScatterPlot

Scatter plot for correlation analysis.

**Configuration**:

```python
{
    "x_column": str,
    "y_column": str,
    "color_by": str,      # Optional: color mapping
    "size_by": str,       # Optional: marker size
    "shape_by": str,      # Optional: marker shape
    "title": str,
}
```

**Example**:

```python
plot = PlotFactory.create_plot("scatter", 1)
plot.config = {
    "x_column": "cache_misses",
    "y_column": "ipc",
    "color_by": "benchmark",
    "title": "IPC vs Cache Misses"
}
fig = plot.create_figure(data)
```

### HistogramPlot

Histogram for distribution visualization.

**Configuration**:

```python
{
    "column": str,        # Data column
    "bins": int,          # Number of bins
    "title": str,
    "color": str,
}
```

## PlotRenderer

### Class: `PlotRenderer`

Renders plots in Streamlit UI.

**Location**: `src/plotting/plot_renderer.py`

#### Methods

##### `render(plot, data)`

Render plot in Streamlit.

**Parameters**:

- `plot` (BasePlot): Plot instance
- `data` (pd.DataFrame): Data to visualize

**Example**:

```python
from src.plotting.plot_renderer import PlotRenderer

renderer = PlotRenderer()
renderer.render(plot, data)
```

## Export Utilities

### Function: `export_plot(fig, filename, format="png")`

Export plot to file.

**Location**: `src/plotting/export.py`

**Parameters**:

- `fig` (go.Figure): Plotly figure
- `filename` (str): Output filename
- `format` (str): Output format ("png", "svg", "pdf", "html")

**Example**:

```python
from src.plotting.export import export_plot

fig = plot.create_figure(data)
export_plot(fig, "ipc_comparison.png", format="png")
export_plot(fig, "ipc_comparison.svg", format="svg")
```

## Styling Utilities

### Function: `apply_publication_style(fig)`

Apply publication-quality styling to figure.

**Location**: `src/plotting/styles/publication.py`

**Features**:

- 14pt+ fonts
- High DPI
- Clean layout
- Vector-ready

**Example**:

```python
from src.plotting.styles.publication import apply_publication_style

fig = plot.create_figure(data)
apply_publication_style(fig)
```

## Color Schemes

### Function: `get_color_palette(name)`

Get predefined color palette.

**Location**: `src/plotting/styles/colors.py`

**Palettes**:

- `"default"` - Plotly default
- `"colorblind"` - Colorblind-friendly
- `"grayscale"` - Grayscale (for printing)
- `"accent"` - High-contrast accent colors

**Returns**: `List[str]` - List of hex colors

**Example**:

```python
from src/plotting.styles.colors import get_color_palette

colors = get_color_palette("colorblind")
plot.config["color_map"] = {
    "baseline": colors[0],
    "optimized": colors[1]
}
```

## Best Practices

1. **Type Hints**: All plotting code uses strict typing
2. **Validation**: Check required columns before plotting
3. **Error Messages**: Provide clear, actionable errors
4. **Immutability**: Never modify input DataFrames
5. **Publication Quality**: Use 14pt+ fonts, vector formats

## Error Handling

### Common Exceptions

**KeyError** (missing column):

```python
try:
    fig = plot.create_figure(data)
except KeyError as e:
    st.error(f"Required column missing: {e}")
```

**ValueError** (invalid config):

```python
try:
    plot.config = {"invalid": "config"}
    fig = plot.create_figure(data)
except ValueError as e:
    st.error(f"Invalid configuration: {e}")
```

## Next Steps

- Shaper API: [Shaper-API.md](Shaper-API.md)
- Creating Plot Types: [../Adding-Plot-Types.md](../Adding-Plot-Types.md)
- Plot References: [../plots/](../plots/)
