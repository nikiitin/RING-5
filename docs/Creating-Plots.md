# Creating Plots Guide

Comprehensive guide to creating and customizing visualizations in RING-5.

## Overview

RING-5 provides seven plot types for gem5 data visualization:

- Bar Chart
- Grouped Bar Chart
- Stacked Bar Chart
- Grouped Stacked Bar Chart
- Line Plot
- Scatter Plot
- Histogram

All plots are built with Plotly for interactivity and publication quality.

## Getting Started

### Prerequisites

- Data loaded via Data Source or Upload Data
- Navigate to **Manage Plots** page

### Creating Your First Plot

1. Click **Create New Plot**
2. Enter plot name (e.g., "IPC Comparison")
3. Select plot type from dropdown
4. Click **Create**

## Plot Types

### Bar Chart

**Purpose**: Compare values across categories

**Configuration**:

- **X-axis**: Categorical variable (e.g., `config`, `benchmark`)
- **Y-axis**: Numeric variable (e.g., `ipc`, `throughput`)

**Use Cases**:

- Compare configurations
- Show single metric per category
- Simple performance comparisons

### Grouped Bar Chart

**Purpose**: Compare multiple groups side-by-side

**Configuration**:

- **X-axis**: Primary category (e.g., `benchmark`)
- **Y-axis**: Numeric variable (e.g., `ipc`)
- **Group by**: Secondary category (e.g., `config`)

**Use Cases**:

- Multi-configuration comparisons per benchmark
- Side-by-side performance metrics
- A/B testing results

### Stacked Bar Chart

**Purpose**: Show composition of totals

**Configuration**:

- **X-axis**: Category (e.g., `benchmark`)
- **Y-axis**: Numeric variable (e.g., `cache_misses`)
- **Stack by**: Component (e.g., `cache_level`)

**Use Cases**:

- Cache hierarchy breakdown
- Memory allocation visualization
- Component contribution analysis

### Grouped Stacked Bar Chart

**Purpose**: Combine grouping and stacking

**Configuration**:

- **X-axis**: Primary category
- **Y-axis**: Numeric variable
- **Group by**: Groups (e.g., `config`)
- **Stack by**: Stack components (e.g., `operation_type`)

**Use Cases**:

- Complex multi-dimensional comparisons
- Showing both configuration and breakdown
- Advanced performance analysis

### Line Plot

**Purpose**: Show trends over continuous variables

**Configuration**:

- **X-axis**: Continuous variable (e.g., `time`, `iteration`)
- **Y-axis**: Metric (e.g., `ipc`, `throughput`)
- **Trace by**: Multiple series (e.g., `config`)

**Use Cases**:

- Time-series analysis
- Convergence plots
- Performance over workload progression

### Scatter Plot

**Purpose**: Visualize relationships between two variables

**Configuration**:

- **X-axis**: First variable (e.g., `cache_miss_rate`)
- **Y-axis**: Second variable (e.g., `ipc`)
- **Color by**: Category (e.g., `config`)
- **Size by**: Third variable (optional)

**Use Cases**:

- Correlation analysis
- Identifying outliers
- Multi-dimensional visualization

### Histogram

**Purpose**: Show distribution of values

**Configuration**:

- **Values**: Variable to analyze (e.g., `ipc`)
- **Bins**: Number of bins (default: auto)
- **Group by**: Optional grouping (e.g., `config`)

**Use Cases**:

- Distribution analysis
- Identifying data patterns
- Performance variability assessment

## Plot Configuration

### Data Mapping

Map DataFrame columns to plot axes:

1. **Select Columns**: Use dropdowns to select columns
2. **Preview**: Check column contents
3. **Validate**: Ensure correct data types

**Tips**:

- X-axis: Usually categorical or time-series
- Y-axis: Always numeric
- Group/Stack: Categorical variables

### Styling Options

Customize plot appearance with title, labels, legend, colors, size, and fonts.

### Layout Options

Control plot layout with margins, grid lines, and axis properties.

## Data Processing Pipeline

Each plot has an independent pipeline for transformations. Order matters: Column Selector → Filter → Sort → Normalize → Mean.

## Best Practices

1. **Choose the right plot type**: Bar for comparison, Stacked for composition, Line for trends
2. **Clean Data First**: Use Data Managers
3. **Publication Quality**: Use 14pt+ fonts
4. **Clear Labels**: Descriptive axis titles

## Next Steps

- **Plot Type References**: Detailed guides for each plot type in [plots/](plots/)
- **Data Transformations**: Master [Shapers](Data-Transformations.md)
- **API Reference**: See [Plotting API](api/Plotting-API.md)

**Need Help?** Check [Troubleshooting](Debugging.md) or open a GitHub issue.
