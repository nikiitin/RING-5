# RING-5

**R**eproducible **I**nstrumentation for **N**umerical **G**raphics for gem5

A modern, reproducible analysis and visualization framework for gem5 simulator output, designed for computer architecture research.

[![CI](https://img.shields.io/badge/CI-passing-success)](https://github.com/vnicolas/RING-5/actions)
[![Tests](https://img.shields.io/badge/tests-653%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-77%25-green)](htmlcov/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Type Checking](https://img.shields.io/badge/mypy-strict%20(0%20errors)-blue)](https://mypy.readthedocs.io/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Features

### 🚀 Core Capabilities

- **Interactive Web UI**: Modern Streamlit dashboard for zero-code analysis
  - Integrated gem5 stats.txt parser
  - Visual pipeline configuration (no JSON required)
  - Interactive plot builder with live preview
  - Portfolio management: Save and restore complete analysis snapshots

- **High-Performance Parsing**:
  - Asynchronous parallel parsing across multiple stats files
  - Automatic variable scanning and type detection
  - Support for scalar, vector, distribution, histogram, and configuration variables

- **Flexible Data Transformation**:
  - Pipeline-based shaper system (normalize, filter, aggregate, sort)
  - Baseline normalization for relative performance analysis
  - Mean calculation (arithmetic, geometric, harmonic)
  - Custom sorting and selection algorithms

- **Plots**:
  - Modern plotting with Plotly (interactive + export)
  - Multiple plot types: bar, line, grouped bar, stacked bar, scatter
  - Advanced styling: custom colors, legends, annotations
  - Vector export (PDF, SVG) and raster formats (PNG)

### 🏗️ Architecture

RING-5 follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│          UI Layer (Streamlit)                   │
│  - Components, Pages, Interactive Widgets       │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓ Uses
┌─────────────────────────────────────────────────┐
│        Service Layer (Business Logic)           │
│  - CsvPoolService, PipelineService              │
│  - PortfolioService, PlotService                │
│  - ParseService, ScannerService                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓ Uses
┌─────────────────────────────────────────────────┐
│      Repository Layer (State Management)        │
│  - ParserStateRepository, DataRepository        │
│  - ConfigRepository, SessionRepository          │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓ Coordinates
┌─────────────────────────────────────────────────┐
│         Domain Layer (Core Logic)               │
│  - Parsers (gem5 types), Workers (async)        │
│  - Shapers (transformations), Plots (rendering) │
└─────────────────────────────────────────────────┘
```

**Key Design Patterns**:

- **Service Layer**: Encapsulates business logic
- **Repository Pattern**: Abstracts state management
- **Factory Pattern**: Creates plots and shapers dynamically
- **Strategy Pattern**: Pluggable transformation algorithms
- **Worker Pool**: Persistent processes for performance
- **Cache-Aside**: Metadata and DataFrame caching

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

### Interactive Web Application

Launch the modern web interface:

```bash
# Start web app
./launch_webapp.sh

# Or directly:
streamlit run app.py
```

Open browser to **[http://localhost:8501](http://localhost:8501)(Port could vary)**

#### Typical Workflow

1. **Parse gem5 Stats**:
   - Navigate to "Data Source" page
   - Enter path to gem5 output directory (e.g., `/home/user/gem5/results`)
   - Set stats file pattern (e.g., `stats.txt` or `*.stats.txt`)
   - Click "Scan Variables" - automatically discovers all available metrics
   - Select variables to parse (IPC, cache miss rates, cycles, etc.)
   - Click "Parse" - generates consolidated CSV

2. **Transform Data**:
   - Go to "Manage Data" page
   - Remove seeds and outliers if needed

3. **Create Visualizations**:
   - Navigate to "Manage Plots" page
   - Click "Add Plot" and select type (grouped bar, line, etc.)
   - Add shapers to pipeline:
     - **Normalize**: Scale relative to baseline configuration
     - **Sort**: Custom categorical ordering (baseline first, etc.)
     - **Mean**: Calculate geometric mean across benchmarks
     - **Filter**: Select top-N or specific subsets
   - Preview results in real-time
   - Configure axes, grouping, colors, and styling
   - Interactive preview with live updates
   - Export to PDF, PNG, SVG, or HTML

4. **Save Portfolio**:
   - Go to "Portfolio" page
   - Save complete workspace (data + plots + pipelines)
   - Load previous analyses for reproducibility

## Configuration Guide

RING-5 uses a single JSON configuration file with three main sections:

**Supported Plot Types:**

| Type          | Description                | Use Case                    |
| ------------- | -------------------------- | --------------------------- |
| `bar`         | Bar plot                   | Comparing categories        |
| `line`        | Line plot                  | Trends over time/values     |
| `grouped_bar` | Multiple bars per category | Multi-metric comparison     |
| `stacked_bar` | Stacked bars               | Part-to-whole relationships |

## Development Guide

### Setup Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd RING-5
make build
source python_venv/bin/activate

# Verify installation
make verify
```

### Running Tests

```bash
# Run all tests (507 tests, 100% passing)
make test

# Run with coverage report (77% coverage)
make test-cov

# Open coverage HTML report
firefox htmlcov/index.html

# Run specific test file
pytest tests/integration/test_parser_functional.py -v

# Run specific test
pytest tests/unit/test_shapers.py::test_normalize_basic -v

# Run with debugger
pytest tests/unit/test_file.py --pdb -s
```

### Type Checking

```bash
# Check all modules with mypy strict
make type-check

# Check specific file
mypy src/web/facade.py --strict --show-error-codes
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Run all quality checks
make lint
```

### Development Workflow

1. **Create Feature Branch**:

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Write Tests First (TDD)**:

   ```python
   # tests/unit/test_my_feature.py
   def test_my_feature():
       # Arrange
       data = create_test_data()
       # Act
       result = my_function(data)
       # Assert
       assert result == expected_value
   ```

3. **Implement Feature**:
   - Follow type hints (all functions, parameters, returns)
   - Add docstrings (Google style with Args/Returns/Raises)
   - Keep functions small and focused
   - Use dependency injection

4. **Verify Quality**:

   ```bash
   make test        # All tests pass
   make type-check  # No type errors
   make lint        # No style issues
   ```

5. **Commit and Push**:
   ```bash
   git add .
   git commit -m "feat: add my new feature"
   git push origin feature/my-new-feature
   ```

### Project Architecture

Follow the layered architecture:

```
UI Layer (web/)
    ↓ calls
Service Layer (services/)
    ↓ calls
Repository Layer (repositories/)
    ↓ calls
Domain Layer (parsers/, plotting/)
```

**Key Principles**:

- **Separation of Concerns**: UI never imports domain logic directly
- **Dependency Injection**: Pass dependencies as parameters
- **Type Safety**: All code is strictly typed (mypy --strict)
- **Async by Default**: Use worker pools for I/O operations
- **Immutability**: DataFrames return new copies, not in-place modifications

### Adding New Features

#### New Plot Type

See [.agent/skills/new-plot-type.md](.agent/skills/new-plot-type.md) for detailed guide.

```python
# 1. Create plot class
from src.plotting.base_plot import BasePlot

class MyPlot(BasePlot):
    def create_figure(self, data: pd.DataFrame) -> go.Figure:
        # Implementation
        pass

# 2. Register in factory
# src/plotting/plot_factory.py
PLOT_REGISTRY = {
    "my_plot": MyPlot,
}

# 3. Write tests
def test_my_plot():
    plot = PlotFactory.create_plot("my_plot", config)
    fig = plot.create_figure(test_data)
    assert isinstance(fig, go.Figure)
```

#### New Shaper (Data Transformation)

See [.agent/skills/shaper-pipeline.md](.agent/skills/shaper-pipeline.md) for detailed guide.

```python
# 1. Create shaper function
def my_shaper(
    data: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    """Apply my transformation."""
    result = data.copy()
    # Transform result
    return result

# 2. Register in factory
# src/web/services/shapers.py
SHAPER_REGISTRY = {
    "my_shaper": my_shaper,
}

# 3. Write tests
def test_my_shaper():
    result = my_shaper(test_data, config)
    assert result.equals(expected_data)
```

#### New Parser Type

See [.agent/workflows/new-variable-type.md](.agent/workflows/new-variable-type.md) for workflow.

### Performance Benchmarks

| Operation           | Before (subprocess) | After (worker pool) | Speedup   |
| ------------------- | ------------------- | ------------------- | --------- |
| Parse 20 variables  | 54.3s               | 1.0s                | **54.3x** |
| Scan 1000 variables | 120s                | 8s                  | **15x**   |
| Full pipeline       | 180s                | 12s                 | **15x**   |

### Contributing

See full guidelines in `CONTRIBUTING.md`.

**Quick Checklist**:

- [ ] All tests pass (`make test`)
- [ ] Type checking passes (`make type-check`)
- [ ] Code formatted (`black src/ tests/`)
- [ ] Docstrings added (Google style)
- [ ] Integration tests added for new features
- [ ] README updated if API changed

### Makefile Targets

| Target         | Description                               |
| -------------- | ----------------------------------------- |
| `make build`   | Check dependencies and install everything |
| `make install` | Install Python dependencies               |
| `make test`    | Run all tests                             |
| `make clean`   | Remove virtual environment                |
| `make help`    | Show available targets                    |
