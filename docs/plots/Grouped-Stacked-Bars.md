---
title: "Grouped Stacked Bars"
nav_order: 12
---

# Grouped Stacked Bar Charts

Complete reference for grouped stacked bar chart visualizations in RING-5.

## Overview

Grouped stacked bar charts combine grouping and stacking for complex multi-dimensional comparisons. Most advanced bar chart type.

## Configuration

**Required**:

- X-axis: Primary category (benchmark)
- Y-axis: Numeric value (cycles, bytes)
- Group by: Secondary category (config)
- Stack by: Components (operation_type)

## Use Cases

### Complex Performance Analysis

Compare configurations with operation breakdown:

```python
X: benchmark
Y: cycles
Group by: config
Stack by: operation
# Groups configs, stacks operations per config
```

### Resource Allocation

Show resource distribution across scenarios:

```python
X: workload
Y: memory_bytes
Group by: allocation_policy
Stack by: memory_type
```

## When to Use

**Use when**:

- Need both grouping and composition
- Comparing complex multi-dimensional data
- Audience is technical

**Avoid when**:

- Simpler charts suffice
- > 4 groups or > 4 stacks
- Audience unfamiliar with chart type

## Styling

### Colors

- Consistent across groups
- Distinct for stack components
- Colorblind-friendly

### Layout

- Clear spacing between groups
- Stack order consistent
- Comprehensive legend

## Best Practices

1. Limit to 3-4 groups
2. Limit to 3-4 stack components
3. Use descriptive legend
4. Consider alternatives first
5. Add percentage mode if needed

## Alternative Approaches

Instead of grouped stacked bars, consider:

- Multiple stacked bar charts (one per group)
- Faceted visualization
- Heat map for many dimensions
- Separate plots for clarity

## Next Steps

- Bar Charts: [Bar-Charts.md](Bar-Charts.md)
- Creating Plots: [../Creating-Plots.md](../Creating-Plots.md)
