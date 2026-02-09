---
title: "Quick Start"
nav_order: 2
---

# Quick Start Guide

Get up and running with RING-5 in just 5 minutes!

## Prerequisites

- **Python 3.12+** installed
- **git** for cloning the repository
- **gem5 stats files** (stats.txt) from your simulations

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/vnicolas/RING-5.git
cd RING-5
```

### 2. Create Virtual Environment

```bash
python3 -m venv python_venv
source python_venv/bin/activate # On Windows: python_venv\Scripts\activate
```

### 3. Install Dependencies

```bash
make dev # Installs all dependencies including dev tools
```

### 4. Verify Installation

```bash
python verify_installation.py
```

You should see:

```python
 All dependencies installed correctly
 RING-5 is ready to use
```

## Your First Analysis

### 1. Launch the Web Interface

```bash
./launch_webapp.sh
# or
streamlit run app.py
```

The app opens at `http://localhost:8501`

### 2. Load gem5 Statistics

1. Navigate to **Data Sources** tab
2. Click **Browse** and select your gem5 stats directory
3. Choose pattern: `stats.txt` or `*.txt`
4. Click **Scan for Variables**

RING-5 discovers all available statistics automatically.

### 3. Select Variables

1. Filter by type: `scalar`, `vector`, `histogram`, etc.
2. Use search to find specific stats (e.g., "ipc", "miss_rate")
3. For vector variables, select which entries you want
4. Click **Add to Selection**

### 4. Parse Data

1. Review selected variables
2. Click **Parse Statistics**
3. Wait for parsing to complete (progress shown)
4. Data loads automatically into the workspace

### 5. Transform Data (Optional)

Apply transformations in the **Data Transformation** tab:

1. **Column Selector** - Keep only relevant columns
2. **Filter** - Remove unwanted rows
3. **Normalize** - Divide by baseline
4. **Rename** - Clean up column names

### 6. Create Your First Plot

1. Go to **Visualization** tab
2. Select plot type: `Bar Chart`
3. Configure:

- **X-axis**: benchmark name
- **Y-axis**: IPC values
- **Title**: "IPC Comparison"

4. Click **Generate Plot**

### 7. Export Results

- **Save Plot**: Download as PNG, PDF, or SVG
- **Save Portfolio**: Preserve entire analysis (data + plots + settings)
- **Export Data**: Save transformed data as CSV

## Next Steps

Now that you've completed your first analysis, explore:

- [**Web Interface Guide**](Web-Interface.md) - Master all features
- [**Parsing Guide**](Parsing-Guide.md) - Advanced parsing workflows
- [**Data Transformations**](Data-Transformations.md) - Complex transformations
- [**Creating Plots**](Creating-Plots.md) - Advanced visualizations

## Common Issues

### Port 8501 Already in Use

```bash
# Kill existing Streamlit instance
pkill -f streamlit

# Or use different port
streamlit run app.py --server.port 8502
```

### Import Errors

```bash
# Reinstall dependencies
make clean
make dev
```

### No Variables Found

- Verify gem5 stats files exist in the directory
- Check file pattern matches your files
- Ensure stats files are not empty

### Parsing Fails

- Check file permissions (need read access)
- Verify stats files are valid gem5 format
- Try with `limit=5` first to test on fewer files

## Example Workflow

Here's a complete workflow for analyzing CPU performance:

```python
# In Python (or use UI equivalently)
from src.web.facade import BackendFacade

facade = BackendFacade()

# 1. Scan for variables
scan_futures = facade.submit_scan_async(
 stats_path="/path/to/gem5/output",
 stats_pattern="stats.txt",
 limit=10
)
scan_results = [f.result() for f in scan_futures]
variables = facade.finalize_scan(scan_results)

# 2. Select IPC variables
selected = [
 {"name": "system.cpu.ipc", "type": "scalar"},
 {"name": "simTicks", "type": "scalar"}
]

# 3. Parse data
import tempfile
output_dir = tempfile.mkdtemp()
parse_futures = facade.submit_parse_async(
 stats_path="/path/to/gem5/output",
 stats_pattern="stats.txt",
 variables=selected,
 output_dir=output_dir,
 scanned_vars=variables
)
parse_results = [f.result() for f in parse_futures]
csv_path = facade.finalize_parsing(output_dir, parse_results)

# 4. Load and visualize
data = facade.load_csv_file(csv_path)
from src.plotting.plot_factory import PlotFactory
plot = PlotFactory.create_plot("bar", plot_id=1, name="IPC Analysis")
fig = plot.create_figure(data, {"x_column": "benchmark", "y_column": "system.cpu.ipc"})
fig.show()
```

## Tips for Success

**Start Small**: Parse 5-10 files first, then scale up
**Use Patterns**: Leverage pattern aggregation (cpu0, cpu1 → cpu\d+)
**Save Portfolios**: Preserve your analysis for reproducibility
**Test Transformations**: Preview data after each shaper
**Export Early**: Save intermediate results as you go

## Getting Help

- **Documentation**: [Full Wiki](Home.md)
- **Issues**: [GitHub Issues](https://github.com/vnicolas/RING-5/issues)
- **Examples**: Check `tests/integration/` for code examples

**Ready to dive deeper?** Continue to [Installation Guide](Installation.md) for detailed setup options.
