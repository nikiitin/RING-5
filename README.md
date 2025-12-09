# RING-5

**Pure Python I**mplementation for a**N**alysis and **G**raphic generation on **gem-5**

A modernized, simplified data analyzer specifically tailored for gem5 simulator output. Fully implemented in Python with no external language dependencies.

## Features

- Pure Python: No R dependencies - everything runs in Python
- Interactive Web UI: Modern Streamlit dashboard for zero-code analysis
  - Integrated Parser: Parse gem5 stats.txt directly in the UI
  - Compression Support: 10-100x faster parsing for remote filesystems
- Simplified Configuration: JSON schema-based configuration with validation
- Template System: Easy configuration file generation with built-in templates
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

# Expected: All tests pass (65 tests)

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

---

### Command Line Interface (For Automation & Scripting)

### 1. Create a Configuration Template

Generate a ready-to-use configuration file:

```bash
python ring5.py create-template \
    --output-path ./my_analysis \
    --stats-path /path/to/gem5/stats \
    --config-file my_config.json \
    --seeds-reducer \
    --add-example-plot
```

Or use the interactive configurator:

```bash
python tools/create_config.py
```

### 2. Validate Configuration

Check your configuration before running:

```bash
python ring5.py validate --config my_config.json
```

### 3. Run Analysis

```bash
# Full pipeline (parse + analyze + plot)
python ring5.py analyze --config my_config.json

# Skip parsing if CSV already exists
python ring5.py analyze --config my_config.json --skip-parse
```

## Configuration Guide

RING-5 uses a single JSON configuration file with three main sections:

### 1. Parse Configuration

Extract data from gem5 stats files:

```json
{
  "parseConfig": {
    "parser": "gem5_stats",
    "statsPath": "/path/to/gem5/output",
    "statsPattern": "**/stats.txt",
    "variables": [
      {"name": "simTicks", "type": "scalar"},
      {"name": "benchmark_name", "type": "configuration"}
    ]
  }
}
```

**Variable Types:**
- `scalar`: Single numeric values (e.g., simTicks, cache misses)
- `vector`: Arrays of values
- `distribution`: Statistical distributions
- `configuration`: Metadata (benchmark names, configuration IDs)

### 2. Data Managers

Preprocess parsed data:

```json
{
  "dataManagers": {
    "seedsReducer": true,
    "outlierRemover": {
      "enabled": true,
      "column": "simTicks",
      "method": "iqr",
      "threshold": 1.5
    },
    "normalizer": {
      "enabled": true,
      "baseline": {"config_description": "baseline_config"},
      "columns": ["simTicks"],
      "groupBy": ["benchmark_name"]
    }
  }
}
```

**Available Managers:**
- **seedsReducer**: Combine multiple random seed runs (mean + std)
- **outlierRemover**: Remove statistical outliers (IQR or z-score)
- **normalizer**: Normalize to baseline configuration

### 3. Plots

Define visualizations:

```json
{
  "plots": [{
    "type": "bar",
    "output": {"filename": "performance", "format": "png", "dpi": 300},
    "data": {
      "x": "benchmark_name",
      "y": "simTicks",
      "hue": "config_description",
      "aggregate": {"method": "geomean", "groupBy": ["config_description"]}
    },
    "style": {
      "title": "Performance Comparison",
      "xlabel": "Benchmark",
      "ylabel": "Normalized Time",
      "grid": true,
      "theme": "whitegrid",
      "legend": {"show": true, "location": "best"}
    }
  }]
}
```

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

**Aggregation Methods:**
- `mean`: Arithmetic mean
- `median`: Median value
- `sum`: Sum of values
- `geomean`: Geometric mean (recommended for normalized values)

**Themes:**
- `default`, `whitegrid`, `darkgrid`, `white`, `dark`, `ticks`

## Complete Example

```json
{
  "outputPath": "./output",
  "parseConfig": {
    "parser": "gem5_stats",
    "statsPath": "/path/to/gem5/stats",
    "variables": [
      {"name": "simTicks", "type": "scalar"},
      {"name": "benchmark_name", "type": "configuration"},
      {"name": "config", "type": "configuration"}
    ]
  },
  "dataManagers": {
    "seedsReducer": true,
    "normalizer": {
      "enabled": true,
      "baseline": {"config": "baseline"},
      "columns": ["simTicks"],
      "groupBy": ["benchmark_name"]
    }
  },
  "plots": [{
    "type": "bar",
    "output": {"filename": "performance"},
    "data": {
      "x": "benchmark_name",
      "y": "simTicks",
      "hue": "config",
      "aggregate": {"method": "geomean", "groupBy": ["config"]}
    },
    "style": {
      "title": "Normalized Performance",
      "ylabel": "Speedup",
      "grid": true
    }
  }]
}
```

## Command Reference

### analyze
Run the full analysis pipeline:
```bash
python ring5.py analyze --config CONFIG [--skip-parse] [--verbose]
```

### validate
Validate configuration file:
```bash
python ring5.py validate --config CONFIG
```

### create-template
Generate configuration template:
```bash
python ring5.py create-template \
    --output-path PATH \
    --stats-path PATH \
    [--config-file FILE] \
    [--seeds-reducer] \
    [--add-example-plot]
```

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

### Project Structure

```
RING-5/
├── ring5.py                    # Main entry point
├── makefile                    # Build and dependency management
├── requirements.txt            # Python dependencies
│
├── schemas/
│   └── config_schema.json      # JSON schema for validation
│
├── templates/
│   └── config_template.json    # Configuration template
│
├── examples/
│   └── complete_example.json   # Full-featured example
│
├── tools/
│   └── create_config.py        # Interactive config generator
│
├── src/
│   ├── config/
│   │   └── config_manager.py   # Config validation & templates
│   ├── plotting/
│   │   └── plot_engine.py      # Python plotting engine
│   ├── data_management/        # Data preprocessing
│   │   └── impl/               # Data manager implementations
│   ├── data_parser/            # Stats file parsing
│   │   └── multiprocessing/    # Parallel parsing
│   └── data_plotter/
│       └── multiprocessing/    # Parallel plotting
│           ├── plotWorkPool.py # Worker pool manager
│           ├── plotWorker.py   # Plot worker process
│           └── plotWork.py     # Work interface
│
└── tests/                      # Test suite
```

## Troubleshooting

### Configuration Validation Errors

Always validate first:
```bash
python ring5.py validate --config my_config.json
```

Common issues:
- Missing required fields (outputPath, parseConfig, plots)
- Invalid plot type names
- Incorrect variable references

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

## Acknowledgments

Built on top of the original R-based RING-5 implementation. This version migrates to pure Python for improved maintainability and ease of use.