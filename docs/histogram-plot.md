# Histogram Plot

## Overview

The **Histogram Plot** visualizes distribution data from gem5 simulator histogram variables. It supports single or multiple histograms grouped by categorical variables, with configurable bucket sizes and normalization modes.

## Features

✅ **Single Histogram** - Display distribution for one variable  
✅ **Grouped Histograms** - Multiple histograms by categorical variable  
✅ **Configurable Bucket Size** - Rebin data to different granularities  
✅ **Normalization Modes** - Count, probability, percent, or density  
✅ **Cumulative Distribution** - Show CDF instead of PDF  
✅ **Publication Quality** - Plotly-based with full styling support

## Usage

### Basic Example

```python
from src.plotting.plot_factory import PlotFactory

# Create histogram plot
plot = PlotFactory.create_plot("histogram", plot_id=1, name="Latency Distribution")

# Configure
config = {
    "histogram_variable": "latency",
    "title": "Request Latency Distribution",
    "xlabel": "Latency (cycles)",
    "ylabel": "Count",
    "bucket_size": 100,
    "normalization": "count",
    "group_by": None,
    "cumulative": False,
}

# Generate figure
fig = plot.create_figure(data, config)
```

### Grouped Histograms

```python
config = {
    "histogram_variable": "latency",
    "title": "Latency by Benchmark",
    "xlabel": "Latency (cycles)",
    "ylabel": "Count",
    "bucket_size": 100,
    "normalization": "count",
    "group_by": "benchmark",  # Group by categorical variable
    "cumulative": False,
}

fig = plot.create_figure(data, config)
```

### Normalized Distribution

```python
config = {
    "histogram_variable": "latency",
    "title": "Latency Probability Distribution",
    "xlabel": "Latency (cycles)",
    "ylabel": "Probability",
    "bucket_size": 100,
    "normalization": "probability",  # Normalize to [0, 1]
    "group_by": None,
    "cumulative": False,
}

fig = plot.create_figure(data, config)
```

### Cumulative Distribution Function (CDF)

```python
config = {
    "histogram_variable": "latency",
    "title": "Cumulative Latency Distribution",
    "xlabel": "Latency (cycles)",
    "ylabel": "CDF",
    "bucket_size": 100,
    "normalization": "probability",
    "group_by": None,
    "cumulative": True,  # Show CDF
}

fig = plot.create_figure(data, config)
```

## Configuration Options

| Parameter | Type | Description | Options |
|-----------|------|-------------|---------|
| `histogram_variable` | str | Base variable name (before "..") | Any histogram variable |
| `title` | str | Plot title | Any string |
| `xlabel` | str | X-axis label | Any string |
| `ylabel` | str | Y-axis label | Any string |
| `bucket_size` | int | Size of histogram buckets | Positive integer |
| `normalization` | str | How to normalize heights | `count`, `probability`, `percent`, `density` |
| `group_by` | str\|None | Categorical variable for grouping | Column name or None |
| `cumulative` | bool | Show cumulative distribution | `true` or `false` |

## Data Format

The histogram plot expects data with columns in this format:

```
variable_name..bucket_range
```

Example columns:
```
latency..0-100
latency..100-200
latency..200-300
latency..300-400
```

### Example DataFrame

```python
import pandas as pd

data = pd.DataFrame({
    "benchmark": ["A", "B"],
    "latency..0-100": [5, 8],
    "latency..100-200": [10, 12],
    "latency..200-300": [15, 18],
    "latency..300-400": [8, 10],
})
```

## Normalization Modes

### Count (Default)
Raw counts from the data.

### Probability
Normalized to sum to 1.0:
```
probability = count / total_count
```

### Percent
Normalized to sum to 100:
```
percent = (count / total_count) * 100
```

### Density
Normalized by bin width:
```
density = count / (total_count * bin_width)
```

## Integration with gem5

Histogram variables from gem5 are automatically detected and can be parsed:

```python
from src.web.facade import BackendFacade

facade = BackendFacade()

# Scan for histogram variables
scan_futures = facade.submit_scan_async(stats_dir, "stats.txt")
scan_results = [f.result() for f in scan_futures]
vars_found = facade.finalize_scan(scan_results)

# Find histogram variable
hist_var = next(v for v in vars_found if v["type"] == "histogram")

# Parse
variables = [{"name": hist_var["name"], "type": "histogram"}]
parse_futures = facade.submit_parse_async(stats_dir, "stats.txt", variables, output_dir)
parse_results = [f.result() for f in parse_futures]
csv_path = facade.finalize_parsing(output_dir, parse_results)

# Load and plot
data = pd.read_csv(csv_path)
plot = PlotFactory.create_plot("histogram", plot_id=1, name="Distribution")
fig = plot.create_figure(data, config)
```

## Testing

Run histogram plot tests:

```bash
# Unit tests
pytest tests/unit/test_histogram_plot.py -v

# Integration tests
pytest tests/integration/test_histogram_plot_integration.py -v

# All histogram tests
pytest -k "histogram" -v
```

## Type Safety

The histogram plot implementation is fully typed with mypy strict mode:

```bash
mypy src/plotting/types/histogram_plot.py --strict
```

## Architecture

The histogram plot follows the project's layered architecture:

- **Layer A (Data)**: Histogram variables parsed from gem5
- **Layer B (Domain)**: `HistogramPlot` class with visualization logic
- **Layer C (Presentation)**: Streamlit UI integration

Uses the **Factory Pattern** for creation and **Strategy Pattern** for different normalization modes.

## Related Documentation

- [New Plot Type Guide](.agent/skills/new-plot-type.md)
- [Variable Types](src/parsers/types/)
- [Plot Factory](src/plotting/plot_factory.py)
- [Base Plot](src/plotting/base_plot.py)
