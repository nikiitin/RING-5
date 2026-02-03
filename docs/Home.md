# RING-5 Documentation

Welcome to the **RING-5** documentation! This wiki provides comprehensive guides for using and developing with RING-5, a modern Python-based analysis and visualization tool for gem5 simulator output.

## Navigation

### Getting Started

- [**Quick Start Guide**](Quick-Start.md) - Get up and running in 5 minutes
- [**Installation**](Installation.md) - Detailed installation instructions
- [**First Analysis**](First-Analysis.md) - Your first gem5 analysis walkthrough

### User Guides

- [**Web Interface Guide**](Web-Interface.md) - Using the Streamlit dashboard
- [**Parsing gem5 Stats**](Parsing-Guide.md) - Complete parsing workflow
- [**Data Transformations**](Data-Transformations.md) - Using shapers and pipelines
- [**Creating Plots**](Creating-Plots.md) - Visualization guide
- [**LaTeX Export Guide**](LaTeX-Export-Guide.md) - Publication-quality export (NEW!)
- [**Portfolio Management**](Portfolios.md) - Saving and sharing analyses

### Plot Types

- [**Bar Charts**](plots/Bar-Charts.md) - Single and grouped bar charts
- [**Line Plots**](plots/Line-Plots.md) - Time-series and trend analysis
- [**Scatter Plots**](plots/Scatter-Plots.md) - Correlation and distribution
- [**Histogram Plots**](plots/Histogram-Plots.md) - Distribution visualization
- [**Grouped Stacked Bars**](plots/Grouped-Stacked-Bars.md) - Complex comparisons

### Developer Guides

- [**Architecture Overview**](Architecture.md) - System design and patterns
- [**Development Setup**](Development-Setup.md) - Setting up your dev environment
- [**Adding New Plot Types**](Adding-Plot-Types.md) - Extending visualization
- [**Adding New Shapers**](Adding-Shapers.md) - Custom data transformations
- [**Testing Guide**](Testing-Guide.md) - Writing and running tests
- [**AI Agent Setup**](AI-Agent-Setup.md) - Using AI assistants for development

### API Reference

- [**Parsing API**](api/Parsing-API.md) - Parse service and scanner
- [**Plotting API**](api/Plotting-API.md) - Plot factory and renderers
- [**Shaper API**](api/Shaper-API.md) - Data transformation interface
- [**Backend Facade**](api/Backend-Facade.md) - Main API entry point

### Advanced Topics

- [**Pattern Aggregation**](Pattern-Aggregation.md) - Handling repeated variables
- [**Async Parsing**](Async-Parsing.md) - Parallel processing internals
- [**Type System**](Type-System.md) - gem5 variable types
- [**Performance Optimization**](Performance.md) - Tips for large datasets
- [**Debugging**](Debugging.md) - Troubleshooting common issues

### Contributing

- [**Contributing Guide**](../CONTRIBUTING.md) - How to contribute
- [**Code Style**](Code-Style.md) - Conventions and standards
- [**Pull Request Process**](PR-Process.md) - Submitting changes
- [**Release Process**](Release-Process.md) - Version management

## Quick Links

| I want to...                    | Go to                                                      |
| ------------------------------- | ---------------------------------------------------------- |
| **Install RING-5**              | [Installation](Installation.md)                            |
| **Parse gem5 stats**            | [Parsing Guide](Parsing-Guide.md)                          |
| **Create a plot**               | [Creating Plots](Creating-Plots.md)                        |
| **Transform data**              | [Data Transformations](Data-Transformations.md)            |
| **Add a feature**               | [Development Setup](Development-Setup.md)                  |
| **Report a bug**                | [GitHub Issues](https://github.com/vnicolas/RING-5/issues) |
| **Understand the architecture** | [Architecture Overview](Architecture.md)                   |
| **Use with AI assistants**      | [AI Agent Setup](AI-Agent-Setup.md)                        |

## What is RING-5?

RING-5 is **Reproducible Instrumentation for Numerical Graphics for gem5**. It provides:

- **Interactive Web UI** - No-code analysis with Streamlit
- **High-Performance Parsing** - Async parallel processing
- **Flexible Transformations** - Pipeline-based data processing
- **Publication-Quality Plots** - Interactive Plotly visualizations
- **Portfolio Management** - Save and restore complete analyses

### Key Features

- **Async-First Architecture** - Efficient parallel processing
- **Strongly Typed** - mypy strict mode, type hints everywhere
- **Test-Driven** - 653+ tests, 77% coverage
- **Layered Design** - Clean separation: Data → Domain → Presentation
- **Extensible** - Factory patterns for plots and transformations

## Documentation Format

This documentation follows these conventions:

- **Code examples** are complete and runnable
- **Type hints** are shown in Python code
- **Commands** are prefixed with `$` for terminal
- **File paths** use Unix conventions (`/path/to/file`)
- **Links** connect related topics

## Learning Path

### For Users

1. Start with [Quick Start Guide](Quick-Start.md)
2. Follow [First Analysis](First-Analysis.md) tutorial
3. Explore [Web Interface Guide](Web-Interface.md)
4. Learn [Data Transformations](Data-Transformations.md)
5. Master [Creating Plots](Creating-Plots.md)

### For Developers

1. Complete [Development Setup](Development-Setup.md)
2. Read [Architecture Overview](Architecture.md)
3. Follow [Testing Guide](Testing-Guide.md)
4. Study [API Reference](api/) docs
5. Review [Contributing Guide](../CONTRIBUTING.md)

### For Researchers

1. Review [Parsing Guide](Parsing-Guide.md) for gem5 specifics
2. Explore [Pattern Aggregation](Pattern-Aggregation.md)
3. Learn [Performance Optimization](Performance.md)
4. Check [Publication Tips](Publication-Tips.md)

## Getting Help

- **Documentation Issues**: [Open a docs issue](https://github.com/vnicolas/RING-5/issues/new?labels=documentation)
- **Bug Reports**: [Open a bug issue](https://github.com/vnicolas/RING-5/issues/new?labels=bug)
- **Feature Requests**: [Open a feature issue](https://github.com/vnicolas/RING-5/issues/new?labels=enhancement)
- **Questions**: Check existing [Discussions](https://github.com/vnicolas/RING-5/discussions)

## License

RING-5 is released under the MIT License. See [LICENSE](../LICENSE) for details.

## Acknowledgments

RING-5 builds upon the gem5 simulator community's work and is designed for researchers in computer architecture (ISCA, MICRO, ASPLOS conferences).

**Version**: 1.0.0
**Last Updated**: February 2026
**Maintained By**: [Contributors](https://github.com/vnicolas/RING-5/graphs/contributors)
