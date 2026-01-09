# RING-5

**Pure Python I**mplementation for a**N**alysis and **G**raphic generation on **gem-5**

A modernized, simplified data analyzer specifically tailored for gem5 simulator output.

## Features

- Interactive Web UI: Modern Streamlit dashboard for zero-code analysis
  - Integrated Parser: Parse gem5 stats.txt directly in the UI
- Modern Plotting: Uses matplotlib, seaborn, and plotly for all visualizations
- Extensible: Easy to add new data managers, shapers, and plot types
- Portfolio Management: Save and restore complete analysis snapshots

## Prerequisites

- Python 3.8 or higher
- GNU bash interpreter on Linux/Debian distribution (Tested: Ubuntu 20.04-LTS)
- pip package manager
- make

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
make test
```

## Quick Start

### Interactive Web Application (Recommended for New Users)

Launch the modern web interface:

```bash
# Start web app
./launch_webapp.sh
```

Open browser to **[http://localhost:8501](http://localhost:8501)** and:

- Parse gem5 stats.txt files directly
  - Interactive variable selection
  - Optional compression for SSHFS/remote filesystems
  - Automatic CSV generation
- Drag-and-drop data upload (or use parsed data)
- Visual pipeline configuration (no JSON needed)
- Interactive plot builder
- One-click exports (CSV, JSON, Excel)
- Automated variable scanning
- Save and load complete portfolios

## Configuration Guide

RING-5 uses a single JSON configuration file with three main sections:

**Supported Plot Types:**

| Type          | Description                | Use Case                    |
| ------------- | -------------------------- | --------------------------- |
| `bar`         | Bar plot                   | Comparing categories        |
| `line`        | Line plot                  | Trends over time/values     |
| `grouped_bar` | Multiple bars per category | Multi-metric comparison     |
| `stacked_bar` | Stacked bars               | Part-to-whole relationships |

## Development

### Running Tests

```bash
# Run all tests
make test
```

### Makefile Targets

| Target         | Description                               |
| -------------- | ----------------------------------------- |
| `make build`   | Check dependencies and install everything |
| `make install` | Install Python dependencies               |
| `make test`    | Run all tests                             |
| `make clean`   | Remove virtual environment                |
| `make help`    | Show available targets                    |
