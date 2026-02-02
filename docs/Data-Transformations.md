# Data Transformations Guide

Complete guide to data transformations using the shaper system in RING-5.

## Overview

RING-5 provides a powerful shaper system for transforming data before visualization:
- **Shapers**: Individual transformation functions
- **Pipelines**: Sequential chains of shapers
- **Immutability**: All operations return new DataFrames

## What is a Shaper?

A shaper is a data transformation function that:
- Takes a DataFrame as input
- Returns a new DataFrame (never modifies in-place)
- Performs one specific transformation
- Can be chained with other shapers

## Available Shapers

### 1. Column Selector

**Purpose**: Select specific columns from the dataset

**Configuration**:
```python
{
    "type": "columnSelector",
    "columns": ["benchmark", "config", "ipc"]
}
```

**Use Case**: Remove unnecessary columns before plotting

**Example**:
```python
# Before: 50 columns
# After: 3 columns (benchmark, config, ipc)
```

### 2. Sort

**Purpose**: Sort data by custom column order

**Configuration**:
```python
{
    "type": "sort",
    "order_dict": {
        "benchmark": ["mcf", "omnetpp", "xalancbmk"],
        "config": ["baseline", "tx_lazy", "tx_eager"]
    }
}
```

**Use Case**: Control the display order in plots

**Example**:
```python
# Sort benchmarks alphabetically
# Then sort configurations by performance
```

### 3. Mean Calculator

**Purpose**: Compute aggregated means (arithmetic, geometric, harmonic)

**Configuration**:
```python
{
    "type": "mean",
    "meanVars": ["ipc", "execution_time"],
    "meanAlgorithm": "geomean",  # or "amean", "hmean"
    "groupingColumns": ["config"],
    "replacingColumn": "benchmark"
}
```

**Use Case**: Add geomean rows for multi-benchmark comparisons

**Example**:
```python
# Original data: mcf, omnetpp, xalancbmk
# Result: mcf, omnetpp, xalancbmk, geomean
```

### 4. Normalize

**Purpose**: Normalize values to a baseline

**Configuration**:
```python
{
    "type": "normalize",
    "normalizeVars": ["ipc", "throughput"],
    "normalizerColumn": "config",
    "normalizerValue": "baseline",
    "groupBy": ["benchmark"]
}
```

**Use Case**: Show relative performance improvements

**Example**:
```python
# Baseline IPC = 1.5
# tx_lazy IPC = 1.8
# Result: tx_lazy normalized = 1.2 (20% improvement)
```

### 5. Filter (Condition Selector)

**Purpose**: Filter rows based on conditions

**Configuration**:
```python
{
    "type": "conditionSelector",
    "column": "benchmark",
    "mode": "equals",  # or "contains", "greater_than", "less_than"
    "threshold": "mcf"
}
```

**Use Case**: Focus on specific benchmarks or configurations

**Example**:
```python
# Filter: ipc > 1.0
# Removes low-performing configurations
```

### 6. Transformer

**Purpose**: Convert column data types

**Configuration**:
```python
{
    "type": "transformer",
    "column": "config",
    "target_type": "factor",  # or "numeric", "string"
    "order": ["baseline", "tx_lazy", "tx_eager"]
}
```

**Use Case**: Control categorical ordering in plots

**Example**:
```python
# Convert config to categorical
# Set specific order for legend/axis
```

## Building Pipelines

### Example 1: Basic Filtering and Sorting

```python
pipeline = [
    # Step 1: Select relevant columns
    {
        "type": "columnSelector",
        "columns": ["benchmark", "config", "ipc"]
    },
    # Step 2: Filter benchmarks
    {
        "type": "conditionSelector",
        "column": "benchmark",
        "mode": "contains",
        "threshold": "spec"
    },
    # Step 3: Sort data
    {
        "type": "sort",
        "order_dict": {
            "benchmark": ["mcf", "omnetpp", "xalancbmk"]
        }
    }
]
```

### Example 2: Normalization Pipeline

```python
pipeline = [
    # Step 1: Normalize to baseline
    {
        "type": "normalize",
        "normalizeVars": ["ipc", "execution_time"],
        "normalizerColumn": "config",
        "normalizerValue": "baseline",
        "groupBy": ["benchmark"]
    },
    # Step 2: Add geometric mean
    {
        "type": "mean",
        "meanVars": ["ipc"],
        "meanAlgorithm": "geomean",
        "groupingColumns": ["config"],
        "replacingColumn": "benchmark"
    },
    # Step 3: Sort for presentation
    {
        "type": "sort",
        "order_dict": {
            "benchmark": ["mcf", "omnetpp", "xalancbmk", "geomean"]
        }
    }
]
```

### Example 3: Multi-Stage Aggregation

```python
pipeline = [
    # Step 1: Filter out warmup phase
    {
        "type": "conditionSelector",
        "column": "phase",
        "mode": "not_equals",
        "threshold": "warmup"
    },
    # Step 2: Aggregate per benchmark
    {
        "type": "mean",
        "meanVars": ["ipc"],
        "meanAlgorithm": "amean",
        "groupingColumns": ["benchmark", "config"],
        "replacingColumn": "seed"
    },
    # Step 3: Compute geomean across benchmarks
    {
        "type": "mean",
        "meanVars": ["ipc"],
        "meanAlgorithm": "geomean",
        "groupingColumns": ["config"],
        "replacingColumn": "benchmark"
    }
]
```

## Using Pipelines in the UI

### In Manage Plots

1. Navigate to **Manage Plots**
2. Select or create a plot
3. Scroll to **Data Processing Pipeline**
4. Click **Add transformation**
5. Select shaper type from dropdown
6. Configure shaper parameters
7. Click **Add to Pipeline**
8. Repeat for additional transformations
9. Click **Update Plot** to apply

### Pipeline Editor Features

- **Reorder**: Drag shapers to reorder pipeline
- **Edit**: Click shaper to modify configuration
- **Delete**: Remove shaper from pipeline
- **Preview**: See transformed data before plotting

## Pipeline Persistence

### Export Pipeline

1. Configure pipeline in plot
2. Click **Export Pipeline**
3. Save JSON file locally

**Format**:
```json
{
  "pipeline": [
    {
      "type": "columnSelector",
      "columns": ["benchmark", "config", "ipc"]
    },
    {
      "type": "normalize",
      "normalizeVars": ["ipc"],
      "normalizerColumn": "config",
      "normalizerValue": "baseline"
    }
  ]
}
```

### Import Pipeline

1. Click **Import Pipeline**
2. Select JSON file
3. Pipeline is loaded into plot

**Use Cases**:
- Reuse pipelines across different datasets
- Share pipelines with collaborators
- Maintain consistent transformations

## Advanced Techniques

### Conditional Transformations

Apply different transformations based on data characteristics:

```python
# If data has seeds, aggregate them first
if "seed" in data.columns:
    pipeline.insert(0, {
        "type": "mean",
        "meanVars": ["ipc"],
        "groupingColumns": ["benchmark", "config"],
        "replacingColumn": "seed"
    })
```

### Multi-Column Operations

Transform multiple columns simultaneously:

```python
{
    "type": "normalize",
    "normalizeVars": ["ipc", "throughput", "latency"],
    "normalizerColumn": "config",
    "normalizerValue": "baseline",
    "groupBy": ["benchmark"]
}
```

### Nested Grouping

Group by multiple levels:

```python
{
    "type": "mean",
    "meanVars": ["ipc"],
    "groupingColumns": ["config", "benchmark"],
    "replacingColumn": "seed"
}
# Groups by config AND benchmark, aggregating seeds
```

## Best Practices

### DO

1. **Start Simple**: Begin with one shaper, verify, then add more
2. **Check Data**: Review transformed data in Data Managers
3. **Use Column Selector Early**: Remove unused columns first
4. **Normalize Last**: Apply normalization after filtering/sorting
5. **Name Columns Clearly**: Rename columns for better plots

### DON'T

1. **Don't Chain Too Many**: Keep pipelines under 5-6 shapers
2. **Don't Normalize Twice**: Multiple normalizations produce incorrect results
3. **Don't Filter Too Aggressively**: Ensure data remains after filters
4. **Don't Ignore Errors**: Pipeline failures indicate data issues

## Troubleshooting

### Pipeline Fails

**Symptoms**: Error message, plot doesn't update

**Solutions**:
- Check column names: Typos in column names
- Verify data exists: Filters may exclude all data
- Review shaper order: Some shapers depend on previous transformations
- Check for missing values: Handle NaN/null before aggregating

### Unexpected Results

**Symptoms**: Plot shows incorrect data

**Solutions**:
- Preview each step: Apply shapers one at a time
- Check data types: Ensure numeric columns are numeric
- Verify normalization baseline: Baseline value must exist in data
- Review grouping columns: Grouping affects aggregation results

### Performance Issues

**Symptoms**: Slow pipeline execution

**Solutions**:
- Reduce data size: Filter early in pipeline
- Simplify aggregations: Avoid complex nested grouping
- Use column selector: Remove unused columns immediately
- Cache results: Store intermediate transformations

## Common Patterns

### Pattern 1: Speedup Calculation

```python
pipeline = [
    {"type": "normalize", "normalizeVars": ["execution_time"], 
     "normalizerColumn": "config", "normalizerValue": "baseline"},
    {"type": "mean", "meanVars": ["execution_time"], 
     "meanAlgorithm": "geomean", "groupingColumns": ["config"]}
]
# Result: Speedup relative to baseline
```

### Pattern 2: Top-K Selection

```python
pipeline = [
    {"type": "sort", "order_dict": {"ipc": "descending"}},
    {"type": "conditionSelector", "column": "rank", 
     "mode": "less_than", "threshold": 10}
]
# Result: Top 10 configurations by IPC
```

### Pattern 3: Outlier Removal

```python
pipeline = [
    {"type": "conditionSelector", "column": "ipc", 
     "mode": "greater_than", "threshold": 0.5},
    {"type": "conditionSelector", "column": "ipc", 
     "mode": "less_than", "threshold": 10.0}
]
# Result: Remove outliers outside [0.5, 10.0]
```

## Integration with Other Features

### With Data Managers

1. Load data via Data Source
2. Apply Data Managers (Outlier Remover, Seeds Reducer)
3. Use shapers for plot-specific transformations

**When to use which**:
- **Data Managers**: Global transformations for all plots
- **Shapers**: Plot-specific transformations

### With Portfolios

Pipelines are saved with plots in portfolios:
- Load portfolio → Pipelines restored
- Pipelines are reusable across sessions

## Next Steps

- **Creating Plots**: Learn about [Plot Creation](Creating-Plots.md)
- **Advanced Plotting**: Explore plot types in [plots/](plots/)
- **API Reference**: See [Shaper API](api/Shaper-API.md)
- **Custom Shapers**: Build custom transformations (advanced)

**Need Help?** Check [Troubleshooting](Debugging.md) or open a GitHub issue.
