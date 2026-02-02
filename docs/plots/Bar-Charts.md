# Bar Charts

Complete reference for bar chart visualizations in RING-5.

## Overview

Bar charts display categorical data with rectangular bars representing values. RING-5 supports four bar chart variants:
- Simple Bar Chart
- Grouped Bar Chart
- Stacked Bar Chart
- Grouped Stacked Bar Chart

## Simple Bar Chart

### Purpose

Compare values across categories with one bar per category.

### Configuration

**Required**:
- X-axis: Categorical column (benchmark, config)
- Y-axis: Numeric column (ipc, throughput)

**Optional**:
- Color: Single color or column-based
- Title and labels
- Legend settings

### Example Use Cases

**Performance Comparison**:
```python
X: config
Y: ipc
# Compares IPC across configurations
```

**Benchmark Analysis**:
```python
X: benchmark
Y: execution_time
# Shows execution time per benchmark
```

### Best Practices

1. Limit categories to 15-20 for readability
2. Sort bars by value for easier comparison
3. Use horizontal bars for long category names
4. Add value labels for precise comparisons

## Grouped Bar Chart

### Purpose

Compare multiple groups side-by-side within each category.

### Configuration

**Required**:
- X-axis: Primary category (benchmark)
- Y-axis: Numeric value (ipc)
- Group by: Secondary category (config)

**Optional**:
- Color scheme per group
- Bar width and spacing
- Legend position

### Example Use Cases

**Multi-Configuration Comparison**:
```python
X: benchmark
Y: ipc
Group by: config
# Shows all configs per benchmark side-by-side
```

**A/B Testing**:
```python
X: workload
Y: throughput
Group by: version
# Compares versions across workloads
```

### Best Practices

1. Limit groups to 5-7 per category
2. Use consistent color scheme
3. Position legend clearly
4. Consider stacked bars if showing composition

## Stacked Bar Chart

### Purpose

Show composition of totals with components stacked vertically.

### Configuration

**Required**:
- X-axis: Category (benchmark)
- Y-axis: Numeric value (cycles, bytes)
- Stack by: Component (operation_type, cache_level)

**Optional**:
- Normalize to 100% (percentage stacking)
- Color per stack component
- Show totals on top

### Example Use Cases

**Cache Hierarchy**:
```python
X: benchmark
Y: misses
Stack by: cache_level
# Shows L1, L2, L3 miss breakdown
```

**Operation Breakdown**:
```python
X: config
Y: cycles
Stack by: operation
# Stacks read, write, compute cycles
```

### Best Practices

1. Limit stack components to 5-7
2. Order stacks logically (largest at bottom)
3. Use diverging colors for contrast
4. Consider percentage mode for proportion analysis

## Grouped Stacked Bar Chart

### Purpose

Combine grouping and stacking for complex multi-dimensional comparisons.

### Configuration

**Required**:
- X-axis: Primary category
- Y-axis: Numeric value
- Group by: Groups within category
- Stack by: Components within groups

**Example**:
```python
X: benchmark
Y: memory_bytes
Group by: config
Stack by: allocation_type
# Groups configs, stacks allocation types
```

### Best Practices

1. Use sparingly - can be complex
2. Ensure clear legend
3. Consider alternatives (faceted plots)
4. Limit to 3-4 groups and 3-4 stacks

## Styling Guidelines

### Colors

**For Simple Bars**:
- Single color: Professional blue/gray
- Color by category: Use consistent palette

**For Grouped Bars**:
- Sequential colors per group
- High contrast between groups
- Colorblind-friendly palettes

**For Stacked Bars**:
- Diverging colors for components
- Consistent colors across charts
- Ordered by intensity

### Labels

**Axis Labels**:
```python
X-axis: "Configuration"
Y-axis: "Instructions Per Cycle (IPC)"
Title: "IPC Comparison Across Configurations"
```

**Value Labels**:
- Show for < 10 bars
- Hide for dense charts
- Format consistently (2 decimal places)

### Fonts

**Publication Quality**:
- Title: 18-20pt bold
- Axis labels: 14-16pt
- Tick labels: 12-14pt
- Value labels: 10-12pt

## Data Preparation

### Column Selection

Use Column Selector shaper:
```python
{
    "type": "columnSelector",
    "columns": ["benchmark", "config", "ipc"]
}
```

### Sorting

Control bar order with Sort shaper:
```python
{
    "type": "sort",
    "order_dict": {
        "benchmark": ["mcf", "omnetpp", "xalancbmk"]
    }
}
```

### Normalization

Show relative performance:
```python
{
    "type": "normalize",
    "normalizeVars": ["ipc"],
    "normalizerColumn": "config",
    "normalizerValue": "baseline"
}
```

## Common Patterns

### Speedup Chart

```python
Pipeline:
  1. Normalize to baseline
  2. Sort by value
  3. Add geomean row
Styling:
  - Horizontal bars
  - Value labels
  - Baseline reference line
```

### Performance Comparison

```python
Pipeline:
  1. Filter top N benchmarks
  2. Sort alphabetically
  3. Add mean aggregation
Styling:
  - Grouped bars by config
  - Consistent colors
  - Clear legend
```

## Troubleshooting

### Bars Too Narrow

- Reduce number of categories
- Increase plot width
- Use horizontal orientation

### Overlapping Labels

- Rotate tick labels 45°
- Use abbreviations
- Increase plot width

### Too Many Groups

- Filter data to top N
- Create separate plots
- Use faceted visualization

## Next Steps

- Line Plots: [Line-Plots.md](Line-Plots.md)
- Scatter Plots: [Scatter-Plots.md](Scatter-Plots.md)
- Histograms: [../histogram-plot.md](../histogram-plot.md)
