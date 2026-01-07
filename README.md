# RING-5

**Pure Python I**mplementation for a**N**alysis and **G**raphic generation on **gem-5**

A modernized, simplified data analyzer specifically tailored for gem5 simulator output.

## Features
- Interactive Web UI: Modern Streamlit dashboard for zero-code analysis
  - Integrated Parser: Parse gem5 stats.txt directly in the UI
  - Compression Support: 10-100x faster parsing for remote filesystems
- Simplified Configuration: JSON schema-based configuration with validation
- Modern Plotting: Uses matplotlib, seaborn, and plotly for all visualizations
- Multithreaded: Parallel plot generation for faster analysis
- Extensible: Easy to add new data managers, shapers, and plot types
- Portfolio Management: Save and restore complete analysis snapshots

## Prerequisites

- Python 3.8 or higher
- GNU bash interpreter on Linux/Debian distribution (Tested: Ubuntu 20.04-LTS)
- pip package manager

## Installation

### Quick Setup (Recommended)

The fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd RING-5

# Build and install (creates virtual environment and installs all dependencies)
make build

# Activate the virtual environment
source python_venv/bin/activate
```

### Manual Installation

If you prefer manual setup or don't have make:

```bash
# Create virtual environment
python3 -m venv python_venv

# Activate it
source python_venv/bin/activate

# Install RING-5 in development mode
pip install -e .
```

### Building Distribution Packages

To create distributable packages:

```bash
# Install build tools
pip install build

# Build wheel and source distribution
python -m build

# This creates:
# - dist/ring5-1.0.0-py3-none-any.whl (wheel package)
# - dist/ring5-1.0.0.tar.gz (source distribution)

# Install from the built wheel
pip install dist/ring5-1.0.0-py3-none-any.whl
```

### Verification

Verify the installation:

```bash
# Run tests
pytest

# Check installed packages
pip list | grep -E "(plotly|streamlit|pandas|matplotlib)"
```

## Quick Start

### Interactive Web Application (Recommended for New Users)

Launch the modern web interface:

```bash
# Activate environment
source python_venv/bin/activate

# Start web app
streamlit run app.py
```

Open browser to **http://localhost:8501** and:
- Parse gem5 stats.txt files directly
  - Interactive variable selection
  - Optional compression for SSHFS/remote filesystems
  - Automatic CSV generation
- Drag-and-drop data upload (or use parsed data)
- Visual pipeline configuration (no JSON needed)
- Interactive plot builder
- One-click exports (CSV, JSON, Excel, PDF)
- Save and load complete portfolios

**See [WEB_APP_README.md](WEB_APP_README.md) for complete web app documentation.**

**See [PARSER_INTEGRATION_GUIDE.md](PARSER_INTEGRATION_GUIDE.md) for parser usage guide.**

**See [VECTOR_PARSING_GUIDE.md](VECTOR_PARSING_GUIDE.md) for vector variable configuration.**

## Configuration Guide

RING-5 uses a single JSON configuration file with three main sections:

**Supported Plot Types:**

| Type | Description | Use Case |
|------|-------------|----------|
| `bar` | Bar plot | Comparing categories |
| `line` | Line plot | Trends over time/values |
| `heatmap` | 2D color-coded matrix | Comparing many configurations |
| `grouped_bar` | Multiple bars per category | Multi-metric comparison |
| `stacked_bar` | Stacked bars | Part-to-whole relationships |
| `box` | Box and whisker | Distribution analysis |
| `violin` | Violin plot | Distribution with density |
| `scatter` | Scatter plot | Correlations |

## API Usage

Use RING-5 components programmatically:

```python
from src.config.config_manager import ConfigTemplateGenerator
from src.plotting.plot_engine import PlotManager

# Create config
config = ConfigTemplateGenerator.create_minimal_config(
    output_path="./output",
    stats_path="/path/to/stats"
)

# Add plot
plot = ConfigTemplateGenerator.create_plot_config(
    "bar", "benchmark", "simTicks", "my_plot",
    title="Performance", grid=True
)
config['plots'].append(plot)

# Generate plots
plot_manager = PlotManager("data.csv", "./output/plots")
plot_manager.generate_plots(config['plots'])
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Or manually
source python_venv/bin/activate
pytest tests/ -v
```


### Import Errors

Ensure all dependencies are installed:
```bash
make install
# or
pip install -r requirements.txt
```

### Plot Generation Errors

- Verify column names in plot config match your CSV
- Check filters reference valid column values
- Ensure aggregation groupBy columns exist

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make build` | Check dependencies and install everything |
| `make install` | Install Python dependencies |
| `make test` | Run all tests |
| `make clean` | Remove virtual environment |
| `make help` | Show available targets |