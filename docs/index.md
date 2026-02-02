---
layout: default
title: RING-5 Documentation
---

# RING-5

**Reproducible Instrumentation for Numerical Graphics for gem5**

A modern, reproducible analysis and visualization framework for gem5 simulator output, designed for computer architecture research.

[![CI](https://img.shields.io/badge/CI-passing-success)](https://github.com/vnicolas/RING-5/actions)
[![Tests](https://img.shields.io/badge/tests-653%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-77%25-green)](htmlcov/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Type Checking](https://img.shields.io/badge/mypy-strict%20(0%20errors)-blue)](https://mypy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Quick Links

- **[Documentation Home](Home.md)** - Start here for complete documentation
- **[Quick Start](Quick-Start.md)** - Get up and running in 5 minutes
- **[Installation Guide](Installation.md)** - Detailed setup instructions
- **[First Analysis Tutorial](First-Analysis.md)** - Step-by-step walkthrough

---

## What is RING-5?

RING-5 is a reproducible Python framework for analyzing and visualizing gem5 simulator output. Built for computer architecture researchers targeting top-tier conferences (ISCA, MICRO, ASPLOS), it combines scientific rigor with engineering excellence.

### Key Features

- **Zero-Hallucination Reproducibility**: Same input → same output, always
- **Interactive Web Interface**: Streamlit dashboard for zero-code analysis
- **High-Performance Parsing**: Asynchronous parallel processing of gem5 stats
- **Publication-Quality Plots**: 7 plot types with full customization
- **Flexible Transformations**: 6 built-in shapers for data manipulation
- **Portfolio Management**: Save and restore complete analysis snapshots

### Architecture Highlights

- **Strongly Typed**: 100% mypy strict mode compliance
- **Test-Driven**: 77% coverage, 653 passing tests
- **Layered Design**: Clean separation (Data → Domain → Presentation)
- **Async-First**: Parallel processing for maximum performance
- **Pattern Aggregation**: Automatic regex consolidation (12,000 → 700 variables)

---

## Getting Started

### Installation

```bash
# Clone repository
git clone https://github.com/vnicolas/RING-5.git
cd RING-5

# Setup environment
python3 -m venv python_venv
source python_venv/bin/activate

# Install dependencies
pip install -e .
```

### Launch Web Interface

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

---

## Documentation Sections

### For Users

| Section | Description |
|---------|-------------|
| [Quick Start](Quick-Start.md) | 5-minute setup and first analysis |
| [Installation](Installation.md) | Complete installation for all platforms |
| [First Analysis](First-Analysis.md) | Detailed walkthrough of your first analysis |
| [Web Interface Guide](Web-Interface.md) | Complete Streamlit UI reference |
| [Data Transformations](Data-Transformations.md) | Shaper system and pipelines |
| [Creating Plots](Creating-Plots.md) | All plot types and configuration |
| [Portfolios](Portfolios.md) | Save and manage analysis snapshots |

### For Developers

| Section | Description |
|---------|-------------|
| [Development Setup](Development-Setup.md) | Dev environment and workflow |
| [Testing Guide](Testing-Guide.md) | TDD approach and testing patterns |
| [Adding Plot Types](Adding-Plot-Types.md) | Extend plotting system |
| [Adding Shapers](Adding-Shapers.md) | Create custom transformations |
| [AI Agent Setup](AI-Agent-Setup.md) | Configure AI assistants for development |

### API Reference

| Section | Description |
|---------|-------------|
| [Parsing API](api/Parsing-API.md) | Scanner and parser services |
| [Plotting API](api/Plotting-API.md) | Plot factory and renderers |
| [Shaper API](api/Shaper-API.md) | Transformation system |
| [Backend Facade](api/Backend-Facade.md) | Unified backend interface |

### Advanced Topics

| Section | Description |
|---------|-------------|
| [Architecture](Architecture.md) | System design and patterns |
| [Parsing Guide](Parsing-Guide.md) | gem5 stats parsing deep dive |

---

## Project Goals

RING-5 embodies three core principles:

1. **Reproducibility**: Zero hallucination, deterministic outputs
2. **Quality**: Publication-grade visualizations, strict typing
3. **Usability**: Zero-code interface, comprehensive documentation

Built for researchers who need reliable, reproducible analysis for their conference submissions.

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Citation

If you use RING-5 in your research, please cite:

```bibtex
@software{ring5,
  title = {RING-5: Reproducible Instrumentation for Numerical Graphics for gem5},
  author = {Nicolas, V.},
  year = {2026},
  url = {https://github.com/vnicolas/RING-5}
}
```

---

**[View Full Documentation →](Home.md)**
