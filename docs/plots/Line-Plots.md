# Line Plots

Complete reference for line plot visualizations in RING-5.

## Overview

Line plots show trends and relationships over continuous variables. Essential for time-series analysis and tracking changes.

## Configuration

**Required**:

- X-axis: Continuous variable (time, iteration, address)
- Y-axis: Metric (ipc, throughput, latency)

**Optional**:

- Trace by: Multiple series (config, benchmark)
- Line style: solid, dashed, dotted
- Markers: points, circles, squares

## Use Cases

### Time-Series Analysis

Track performance over simulation time:

```python
X: simTicks
Y: ipc
Trace by: config
# Shows IPC evolution over time
```

### Convergence Plots

Monitor algorithm convergence:

```python
X: iteration
Y: error_rate
Trace by: algorithm
# Shows convergence speed
```

### Workload Progression

Analyze behavior across workload phases:

```python
X: instruction_count
Y: cache_miss_rate
Trace by: cache_level
# Shows miss rate progression
```

## Styling

### Line Properties

- Width: 2-3px for primary lines
- Style: Solid for main, dashed for reference
- Opacity: 0.8-1.0

### Markers

- Show for sparse data (< 50 points)
- Hide for dense data
- Size: 6-8px

### Colors

Use distinct colors per trace:

- Maximum 7 traces per plot
- Colorblind-friendly palette
- Consistent across related plots

## Data Preparation

### Filtering

Remove warmup phase:

```python
{
    "type": "conditionSelector",
    "column": "phase",
    "mode": "not_equals",
    "threshold": "warmup"
}
```

### Sorting

Ensure chronological order:

```python
{
    "type": "sort",
    "order_dict": {"simTicks": "ascending"}
}
```

## Best Practices

1. Limit to 5-7 traces per plot
2. Use consistent time units
3. Add reference lines for baselines
4. Label key events/phases
5. Use log scale for exponential data

## Common Patterns

### Multi-Config Comparison

```python
X: time
Y: throughput
Trace by: config
Pipeline: Filter → Sort
```

### Phase Analysis

```python
X: phase_id
Y: ipc
Trace by: benchmark
Pipeline: Aggregate by phase
```

## Next Steps

- Scatter Plots: [Scatter-Plots.md](Scatter-Plots.md)
- Bar Charts: [Bar-Charts.md](Bar-Charts.md)
