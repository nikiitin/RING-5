# First Analysis Guide

Complete walkthrough of your first gem5 data analysis with RING-5.

## Prerequisites

- RING-5 installed and running
- gem5 simulator output directory containing `stats.txt` files
- Basic understanding of gem5 statistics

## Overview

This guide covers:
1. Launching the web application
2. Loading gem5 data via parsing
3. Visualizing statistics
4. Applying data transformations
5. Saving your analysis

## Step 1: Launch the Application

Start the RING-5 web interface:

```bash
cd RING-5
./launch_webapp.sh
```

The application opens at `http://localhost:8501`.

## Step 2: Navigate to Data Source

1. In the sidebar, select **Data Source**
2. You'll see two options:
   - **Parse gem5 Stats**: Parse gem5 simulator output
   - **Upload CSV**: Upload pre-parsed data

Choose **Parse gem5 Stats** for this tutorial.

## Step 3: Configure Parsing

### Select gem5 Output Directory

1. Click **Browse** to select your gem5 output directory
2. The directory should contain `stats.txt` files
3. Enter the stats file pattern (default: `stats.txt`)

### Scan for Variables

1. Click **Scan Variables**
2. Wait for scanning to complete (progress bar shows status)
3. Review discovered variables in the table

**What is scanning?**
Scanning discovers all available statistics in your gem5 output without parsing values. It identifies:
- Variable names (e.g., `system.cpu.ipc`)
- Variable types (scalar, vector, histogram, distribution)
- Available entries for vector variables

### Select Variables to Parse

1. Review the scanned variables table
2. Select variables you want to analyze:
   - `system.cpu.ipc` (scalar)
   - `system.cpu.numCycles` (scalar)
   - `system.cpu.dcache.overall_miss_rate` (scalar)
3. Click **Parse Selected Variables**

**Pattern Variables**:
Notice variables like `system.cpu\d+.ipc` - these are pattern aggregations where multiple components (cpu0, cpu1, cpu2) are consolidated into a single regex pattern.

### Wait for Parsing

Parsing extracts actual data values from stats.txt files:
- Progress bar shows completion percentage
- Parsing runs asynchronously for speed
- Large datasets may take several minutes

## Step 4: Review Loaded Data

Once parsing completes:

1. The **Current Dataset** section shows:
   - Number of rows
   - Number of columns
   - Data source path

2. Navigate to **Data Managers** to inspect the data:
   - View raw data in table format
   - Check column names and types
   - Verify data was parsed correctly

## Step 5: Create Your First Plot

### Navigate to Manage Plots

1. In the sidebar, select **Manage Plots**
2. Click **Create New Plot**

### Configure Plot

1. **Select Plot Type**:
   - Bar Chart
   - Grouped Bar Chart
   - Line Plot
   - Scatter Plot
   - Histogram

2. **Name Your Plot**:
   - Enter descriptive name (e.g., "IPC Comparison")

3. **Click Create**

### Configure Plot Mapping

For a bar chart comparing IPC across configurations:

1. **X-axis**: Select `config` (configuration name)
2. **Y-axis**: Select `system.cpu.ipc`
3. **Group by** (optional): Select `benchmark` for grouped bars

### Apply Data Transformations (Optional)

Add transformations in the **Data Processing Pipeline**:

1. **Column Selector**: Keep only needed columns
2. **Filter**: Remove outliers or specific benchmarks
3. **Normalize**: Normalize values to baseline configuration
4. **Sort**: Order data for better visualization

Example pipeline:
```python
# 1. Select columns
{"type": "columnSelector", "columns": ["config", "benchmark", "ipc"]}

# 2. Filter benchmarks
{"type": "conditionSelector", "column": "benchmark", "mode": "equals", "value": "mcf"}

# 3. Normalize to baseline
{"type": "normalize", "normalizeVars": ["ipc"], "normalizerColumn": "config", "normalizerValue": "baseline"}
```

### Generate Plot

Click **Update Plot** to render the visualization.

## Step 6: Customize Your Plot

### Plot Configuration

Customize appearance:

1. **Title**: Update plot title
2. **Axis Labels**: Customize X/Y axis labels
3. **Legend**: Show/hide legend, adjust position
4. **Colors**: Change color scheme
5. **Size**: Adjust plot dimensions

### Interactive Features

Use Plotly's interactive tools:

- **Zoom**: Box zoom or scroll zoom
- **Pan**: Click and drag
- **Hover**: View exact values
- **Legend**: Click to hide/show traces
- **Download**: Export as PNG

## Step 7: Create Multiple Plots

Create additional plots for comparison:

1. Click **Create New Plot**
2. Select different plot type
3. Configure different variables
4. Apply different transformations

**Tip**: Each plot has its own independent data pipeline.

## Step 8: Save Your Analysis

### Create a Portfolio

Save your complete analysis session:

1. Navigate to **Portfolio** in sidebar
2. Click **Save Portfolio**
3. Enter portfolio name (e.g., "IPC Analysis 2026-02")
4. Optional: Add description
5. Click **Save**

**What gets saved?**
- All loaded data
- All plot configurations
- All data pipelines
- All transformations

### Load Saved Portfolio

Restore a previous session:

1. Navigate to **Portfolio**
2. Select saved portfolio from dropdown
3. Click **Load Portfolio**
4. All plots and data are restored

## Common Issues

### "No data loaded"

**Solution**: Navigate to Data Source and parse or upload data first.

### "Variable not found after parsing"

**Solution**: Check variable name spelling, ensure it was selected during parsing.

### "Parsing takes too long"

**Solutions**:
- Reduce number of files: Use `limit` parameter in scan
- Select fewer variables: Parse only needed statistics
- Check file size: Very large stats.txt files take longer

### "Plot shows no data"

**Solutions**:
- Check data pipeline: Filters may be excluding all data
- Verify column names: Ensure mapped columns exist
- Review data: Use Data Managers to inspect loaded data

## Next Steps

- **Data Transformations**: Learn about [Data Transformations](Data-Transformations.md)
- **Advanced Plotting**: Explore [Creating Plots](Creating-Plots.md)
- **Shapers**: Master [Shaper Pipelines](Parsing-Guide.md)
- **Pattern Aggregation**: Understand [Pattern Aggregation](Pattern-Aggregation.md)

## Tips for Effective Analysis

1. **Start Small**: Parse a subset of files first (use `limit` parameter)
2. **Incremental Approach**: Add transformations one at a time
3. **Save Often**: Create portfolios for important analyses
4. **Name Descriptively**: Use clear names for plots and portfolios
5. **Check Data**: Always review raw data in Data Managers first

**Need Help?** Check [Troubleshooting](Debugging.md) or open a GitHub issue.
