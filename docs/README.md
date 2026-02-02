# RING-5 Documentation

Welcome to the comprehensive documentation for **RING-5: Reproducible Instrumentation for Numerical Graphics for gem5** - a modern, reproducible analysis and visualization framework for gem5 simulator output.

## Available Documentation

This documentation is organized into several categories to help you find what you need quickly.

### Getting Started (New Users Start Here!)

| Document | Description |
|----------|-------------|
| [**Quick Start Guide**](Quick-Start.md) | Get up and running in 5 minutes |
| [**Installation**](Installation.md) | Detailed installation for all platforms |
| [**First Analysis**](First-Analysis.md) | Step-by-step first analysis walkthrough |

### User Guides

| Document | Description |
|----------|-------------|
| [**Web Interface Guide**](Web-Interface.md) | Master the Streamlit dashboard |
| [**Parsing gem5 Stats**](Parsing-Guide.md) | Complete parsing workflow |
| [**Data Transformations**](Data-Transformations.md) | Using shapers and pipelines |
| [**Creating Plots**](Creating-Plots.md) | Visualization guide |
| [**Portfolio Management**](Portfolios.md) | Saving and sharing analyses |

### Plot Type References

| Document | Description |
|----------|-------------|
| [**Bar Charts**](plots/Bar-Charts.md) | Single and grouped bar charts |
| [**Line Plots**](plots/Line-Plots.md) | Time-series and trend analysis |
| [**Scatter Plots**](plots/Scatter-Plots.md) | Correlation and distribution |
| [**Histogram Plots**](histogram-plot.md) | Distribution visualization |
| [**Grouped Stacked Bars**](plots/Grouped-Stacked-Bars.md) | Complex comparisons |

### Developer Guides

| Document | Description |
|----------|-------------|
| [**Architecture Overview**](Architecture.md) | System design and patterns |
| [**Development Setup**](Development-Setup.md) | Setting up dev environment |
| [**Testing Guide**](Testing-Guide.md) | Writing and running tests |
| [**Adding Plot Types**](Adding-Plot-Types.md) | Extending visualization |
| [**Adding Shapers**](Adding-Shapers.md) | Custom transformations |
| [**AI Agent Setup**](AI-Agent-Setup.md) | Using AI for development |

### API Reference

| Document | Description |
|----------|-------------|
| [**Parsing API**](api/Parsing-API.md) | Parse service and scanner |
| [**Plotting API**](api/Plotting-API.md) | Plot factory and renderers |
| [**Shaper API**](api/Shaper-API.md) | Data transformation interface |
| [**Backend Facade**](api/Backend-Facade.md) | Main API entry point |

### Advanced Topics

| Document | Description |
|----------|-------------|
| [**Pattern Aggregation**](Pattern-Aggregation.md) | Handling repeated variables |
| [**Async Parsing**](Async-Parsing.md) | Parallel processing internals |
| [**Type System**](Type-System.md) | gem5 variable types |
| [**Performance**](Performance.md) | Optimization tips |
| [**Debugging**](Debugging.md) | Troubleshooting guide |

### Contributing

| Document | Description |
|----------|-------------|
| [**Contributing Guide**](../CONTRIBUTING.md) | How to contribute |
| [**Code Style**](Code-Style.md) | Conventions and standards |
| [**PR Process**](PR-Process.md) | Submitting changes |

## Quick Navigation

### I want to...

- **Install RING-5** → [Installation Guide](Installation.md)
- **Start using RING-5** → [Quick Start](Quick-Start.md)
- **Parse gem5 stats** → [Parsing Guide](Parsing-Guide.md)
- **Create visualizations** → [Creating Plots](Creating-Plots.md)
- **Transform data** → [Data Transformations](Data-Transformations.md)
- **Understand architecture** → [Architecture Overview](Architecture.md)
- **Contribute code** → [Contributing Guide](../CONTRIBUTING.md)
- **Report a bug** → [GitHub Issues](https://github.com/vnicolas/RING-5/issues)
- **Use AI assistants** → [AI Agent Setup](AI-Agent-Setup.md)

## Documentation Search

Can't find what you're looking for? Here are some tips:

1. **Use GitHub's search**: Press `/` to search within this repository
2. **Check the sidebar**: Navigation menu on the left (GitHub Wiki)
3. **Browse by category**: See sections above
4. **Search issues**: Someone may have asked before
5. **Ask in discussions**: [GitHub Discussions](https://github.com/vnicolas/RING-5/discussions)

## Documentation Format

All documentation follows these conventions:

- **Code examples** are complete and runnable
- **Type hints** are shown in Python code
- **Commands** use `$` prefix for terminal
- **File paths** use Unix format (`/path/to/file`)
- **Links** connect related topics
- **Tables** for quick reference

## Learning Paths

### Path 1: User (No Programming)

1. [Quick Start](Quick-Start.md) - Get started fast
2. [Web Interface](Web-Interface.md) - Master the UI
3. [Creating Plots](Creating-Plots.md) - Make visualizations
4. [Portfolios](Portfolios.md) - Save your work

**Time**: ~1-2 hours

### Path 2: Power User (Some Python)

1. [Installation](Installation.md) - Set up properly
2. [Parsing Guide](Parsing-Guide.md) - Understand parsing
3. [Data Transformations](Data-Transformations.md) - Process data
4. [Pattern Aggregation](Pattern-Aggregation.md) - Advanced patterns
5. [Performance](Performance.md) - Optimize workflows

**Time**: ~3-4 hours

### Path 3: Developer (Contributing)

1. [Development Setup](Development-Setup.md) - Dev environment
2. [Architecture](Architecture.md) - Understand design
3. [Testing Guide](Testing-Guide.md) - Write tests
4. [API Reference](api/) - Study APIs
5. [Contributing](../CONTRIBUTING.md) - Submit PRs

**Time**: ~6-8 hours

### Path 4: Researcher (Publications)

1. [Parsing Guide](Parsing-Guide.md) - gem5 specifics
2. [Data Transformations](Data-Transformations.md) - Analysis
3. [Creating Plots](Creating-Plots.md) - Publication quality
4. [Performance](Performance.md) - Large datasets
5. [Debugging](Debugging.md) - Troubleshooting

**Time**: ~4-5 hours

## Getting Help

### Documentation Issues

Found an error or missing info? [Open a docs issue](https://github.com/vnicolas/RING-5/issues/new?labels=documentation&template=docs.md)

### Bug Reports

Something not working? [Open a bug report](https://github.com/vnicolas/RING-5/issues/new?labels=bug&template=bug_report.md)

### Feature Requests

Have an idea? [Open a feature request](https://github.com/vnicolas/RING-5/issues/new?labels=enhancement&template=feature_request.md)

### Questions

Not sure about something? Check [Discussions](https://github.com/vnicolas/RING-5/discussions)

## Documentation Updates

This documentation is actively maintained:

- **Version**: 1.0.0
- **Last Major Update**: February 2026
- **Update Frequency**: Continuous
- **Maintainers**: [Contributors](https://github.com/vnicolas/RING-5/graphs/contributors)

### Contributing to Docs

Documentation improvements are always welcome! See [Contributing Guide](../CONTRIBUTING.md) for:

- Fixing typos and errors
- Adding examples
- Improving explanations
- Adding new guides
- Translating docs (future)

## License

RING-5 and its documentation are released under the MIT License. See [LICENSE](../LICENSE) for details.

## Acknowledgments

RING-5 is built for the gem5 simulator community and researchers in computer architecture conferences (ISCA, MICRO, ASPLOS).

Special thanks to all [contributors](https://github.com/vnicolas/RING-5/graphs/contributors) who have helped improve this project and documentation.

## Next Steps

Choose your path:

- **New to RING-5?** → Start with [Quick Start Guide](Quick-Start.md)
- **Want to understand the system?** → Read [Architecture Overview](Architecture.md)
- **Ready to contribute?** → Check [Contributing Guide](../CONTRIBUTING.md)
- **Need specific info?** → Use the navigation sidebar or search above

**Happy analyzing!** 
