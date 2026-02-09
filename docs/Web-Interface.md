---
title: "Web Interface"
nav_order: 5
---

# Web Interface Guide

Comprehensive guide to the RING-5 Streamlit web interface.

## Overview

The RING-5 web application provides an interactive dashboard for:

- Parsing gem5 simulator output
- Transforming and filtering data
- Creating publication-quality visualizations
- Managing analysis portfolios

## Application Structure

### Navigation Sidebar

The sidebar provides access to all pages:

1. **Home**: Application overview and dataset preview
2. **Data Source**: Parse gem5 stats or upload CSV files
3. **Data Managers**: View and transform data
4. **Upload Data**: Direct CSV upload
5. **Manage Plots**: Create and configure visualizations
6. **Portfolio**: Save and load analysis sessions
7. **Performance**: Monitor application performance

### Current Dataset Display

When data is loaded, the main page shows:

- **Rows**: Number of data points
- **Columns**: Number of variables
- **Source**: Data origin (parsed path or uploaded file)

## Pages in Detail

### 1. Data Source Page

**Purpose**: Load data into RING-5

#### Parse gem5 Stats

**Workflow**:

1. Select gem5 output directory
2. Configure stats file pattern (default: `stats.txt`)
3. Click **Scan Variables**
4. Review discovered variables
5. Select variables to parse
6. Click **Parse Selected Variables**
7. Wait for completion

**Pattern Aggregation**:
Variables with repeated indices (cpu0, cpu1, cpu2) are consolidated into regex patterns (cpu\d+).

**Scan Configuration**:

- **Limit**: Number of files to scan (-1 for all)
- **Pattern**: Glob pattern for stats files
- **Recursive**: Search subdirectories

#### Upload CSV

**Workflow**:

1. Click **Browse** to select CSV file
2. Review preview
3. Click **Upload**
4. Data is loaded into session

**CSV Requirements**:

- First row must be column headers
- UTF-8 encoding recommended
- Comma-separated values

### 2. Data Managers Page

**Purpose**: View, filter, and transform loaded data

#### Tabs

**Visualization Tab**:

- Full data table view
- Search functionality
- Column filtering
- Pagination support
- Download filtered view as CSV

**Operations**:

- Search across all columns
- Filter by column value
- Sort by columns
- Export current view

**Seeds Reducer**:
Aggregate multiple seeds/runs:

- Group by configuration and benchmark
- Apply aggregation function (mean, median, geomean)
- Reduce variance from multiple runs

**Mixer**:
Merge multiple datasets:

- Combine data from different sources
- Join on common columns
- Useful for multi-experiment comparisons

**Outlier Remover**:
Identify and remove statistical outliers:

- Z-score method
- IQR method
- Custom threshold

**Preprocessor**:
Clean and prepare data:

- Handle missing values
- Convert data types
- Rename columns

### 3. Manage Plots Page

**Purpose**: Create and configure visualizations

#### Creating Plots

1. Click **Create New Plot**
2. Select plot type:
   - Bar Chart
   - Grouped Bar Chart
   - Stacked Bar Chart
   - Grouped Stacked Bar Chart
   - Line Plot
   - Scatter Plot
   - Histogram
3. Enter plot name
4. Click **Create**

#### Plot Configuration

Each plot has independent configuration:

**Data Mapping**:

- **X-axis**: Variable for horizontal axis
- **Y-axis**: Variable for vertical axis
- **Group by**: Variable for grouping (grouped plots)
- **Stack by**: Variable for stacking (stacked plots)
- **Color by**: Variable for color coding

**Data Processing Pipeline**:
Add transformations sequentially:

1. **Column Selector**: Keep specific columns
2. **Sort**: Order data
3. **Mean Calculator**: Add aggregated means
4. **Normalize**: Normalize to baseline
5. **Filter**: Apply conditions
6. **Transformer**: Custom transformations

**Plot Styling**:

- Title and labels
- Legend position
- Color scheme
- Size dimensions
- Grid lines
- Font sizes

#### Managing Multiple Plots

**Plot Selector**:
Dropdown to switch between plots

**Plot Controls**:

- **Rename**: Update plot name
- **Delete**: Remove plot
- **Duplicate**: Create copy
- **Export Pipeline**: Save pipeline configuration
- **Import Pipeline**: Load pipeline from file

### 4. Upload Data Page

**Purpose**: Direct CSV file upload

**Features**:

- Drag-and-drop support
- File preview before upload
- Column type detection
- Error handling for malformed CSV

**Use Cases**:

- Pre-processed data
- External analysis results
- Manual data entry exports

### 5. Portfolio Page

**Purpose**: Save and load complete analysis sessions

#### Saving Portfolios

1. Click **Save Portfolio**
2. Enter portfolio name
3. Optional: Add description
4. Click **Save**

**Saved Content**:

- All loaded data (DataFrame)
- All plot objects (configurations + pipelines)
- All transformations
- All session state

#### Loading Portfolios

1. Select portfolio from dropdown
2. Click **Load Portfolio**
3. Session is restored completely

**Format**:
Portfolios are saved as JSON files containing serialized data and configurations.

### 6. Performance Page

**Purpose**: Monitor application performance and resource usage

**Metrics**:

- **Parse Operations**: Number of parse tasks
- **Worker Pool Size**: Concurrent workers
- **CSV Cache**: Cached CSV files
- **Session State Size**: Number of state keys
- **Memory Usage**: DataFrame sizes

**Actions**:

- **Clear All Caches**: Reset CSV pool cache
- **Monitor Performance**: Real-time metrics

## State Management

### Session State

RING-5 uses Streamlit session state for:

- Loaded data (`data`)
- Plot objects (`plots_objects`)
- Parsed variables (`parse_variables`)
- Scanned variables (`scanned_variables`)
- Configuration settings

**State Persistence**:
Session state is **not** persistent across browser sessions. Use portfolios for persistence.

### StateManager API

Central state management through `StateManager` class:

```python
from src.web.state_manager import StateManager

# Get data
data = StateManager.get_data()

# Set data
StateManager.set_data(new_data)

# Check if data exists
if StateManager.has_data():
    # Process data
```

## Interactive Features

### Plotly Interactivity

All plots support:

- **Zoom**: Box zoom, scroll zoom
- **Pan**: Click and drag
- **Hover**: Inspect data points
- **Legend Toggle**: Click to show/hide traces
- **Download**: Export as PNG/SVG
- **Relayout**: Drag axes to resize

### Real-time Updates

Changes trigger automatic updates:

- Adding/removing shapers
- Updating plot configuration
- Changing data mapping
- Applying filters

## Keyboard Shortcuts

- **Ctrl+R** / **Cmd+R**: Rerun application
- **Ctrl+Click** on link: Open in new tab
- **Escape**: Close modals/dialogs

## Data Flow

```text
gem5 Output Directory
        ↓
    [Scan Variables]
        ↓
    [Select Variables]
        ↓
    [Parse Stats]
        ↓
    [Load Data] → StateManager
        ↓
    [Apply Shapers] → Pipeline
        ↓
    [Create Plot] → Visualization
        ↓
    [Save Portfolio] → JSON File
```

## Best Practices

1. **Load Data First**: Always load data before creating plots
2. **Use Meaningful Names**: Name plots descriptively
3. **Save Regularly**: Create portfolios for important analyses
4. **Pipeline Incrementally**: Add transformations one at a time
5. **Review Data**: Check Data Managers before plotting
6. **Export Pipelines**: Save pipeline configurations for reuse

## Common Workflows

### Workflow 1: Quick Analysis

1. Data Source → Parse gem5 Stats
2. Scan → Select → Parse
3. Manage Plots → Create Plot
4. Configure → Visualize
5. Portfolio → Save

### Workflow 2: Multi-Configuration Comparison

1. Upload CSV with pre-processed data
2. Data Managers → Review data
3. Manage Plots → Create Grouped Bar Chart
4. Configure grouping by configuration
5. Apply normalization to baseline
6. Save portfolio

### Workflow 3: Publication Figure

1. Parse gem5 stats
2. Apply shapers: Filter → Sort → Normalize
3. Create plot with custom styling
4. Adjust fonts, colors, legend
5. Export as PNG (high resolution)
6. Save pipeline for reproducibility

## Troubleshooting

### Application Not Loading

**Solutions**:

- Check terminal for errors
- Ensure port 8501 is not in use
- Restart application: `Ctrl+C` then `./launch_webapp.sh`

### Data Not Appearing

**Solutions**:

- Verify data was loaded (check Current Dataset)
- Check session state: Performance page
- Try reloading: Press `R` key

### Plot Not Updating

**Solutions**:

- Click **Update Plot** button
- Check pipeline for errors
- Review data mapping
- Verify data exists after transformations

### Session State Lost

**Solutions**:

- Session state resets on browser close
- Save portfolios before closing
- Use portfolio to restore session

## Advanced Features

### Custom Plotly Configuration

Access Plotly config in plot settings:

- Modebar buttons
- Display logo
- Responsive sizing
- Scroll zoom

### Pipeline Import/Export

Share pipeline configurations:

1. Export pipeline as JSON
2. Share file with collaborators
3. Import on different dataset
4. Pipeline is reusable across projects

### Data Manager Chaining

Chain multiple data managers:

1. Outlier Remover → Remove statistical outliers
2. Seeds Reducer → Aggregate runs
3. Preprocessor → Clean column names

## Next Steps

- **Data Transformations**: [Data Transformations Guide](Data-Transformations.md)
- **Creating Plots**: [Plot Creation Guide](Creating-Plots.md)
- **Portfolios**: Advanced portfolio management
- **API Reference**: [Backend Facade API](api/Backend-Facade.md)

**Need Help?** See [Troubleshooting](Debugging.md) or open an issue on GitHub.
