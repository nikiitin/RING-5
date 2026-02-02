# Scatter Plots

Complete reference for scatter plot visualizations in RING-5.

## Overview

Scatter plots visualize relationships between two continuous variables. Essential for correlation analysis and outlier detection.

## Configuration

**Required**:
- X-axis: First variable (cache_miss_rate)
- Y-axis: Second variable (ipc)

**Optional**:
- Color by: Category (config, benchmark)
- Size by: Third variable (execution_time)
- Shape by: Another category

## Use Cases

### Correlation Analysis

Identify relationships between metrics:
```python
X: cache_miss_rate
Y: ipc
Color by: config
# Shows IPC vs miss rate correlation
```

### Outlier Detection

Find anomalous data points:
```python
X: memory_bandwidth
Y: execution_time
Color by: benchmark
# Identifies outliers
```

### Multi-Dimensional Visualization

Show three dimensions:
```python
X: cache_misses
Y: ipc
Size by: instruction_count
Color by: config
# Three metrics in one plot
```

## Styling

### Marker Properties

- Size: 6-10px (or variable)
- Opacity: 0.6-0.8 for overlapping points
- Shape: Circle (default), square, triangle

### Colors

- By category: Distinct colors
- By value: Sequential or diverging scale
- Transparency for density

## Data Preparation

### Filtering

Remove outliers if needed:
```python
{
    "type": "conditionSelector",
    "column": "ipc",
    "mode": "between",
    "min": 0.5,
    "max": 10.0
}
```

### Normalization

Scale variables for comparison:
```python
{
    "type": "normalize",
    "normalizeVars": ["x_var", "y_var"]
}
```

## Best Practices

1. Use transparency for dense data
2. Add trend lines for correlation
3. Limit color categories to 5-7
4. Use log scale for wide ranges
5. Annotate key points

## Common Patterns

### Performance Correlation

```python
X: metric_1
Y: metric_2
Color by: config
Pipeline: Filter outliers
Styling: Add trend line
```

### Benchmark Clustering

```python
X: ipc
Y: cache_miss_rate
Color by: benchmark_suite
Pipeline: Normalize
```

## Next Steps

- Histograms: [../histogram-plot.md](../histogram-plot.md)
- Line Plots: [Line-Plots.md](Line-Plots.md)
