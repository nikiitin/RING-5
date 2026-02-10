---
layout: default
title: Home
nav_order: 1
permalink: /
---

# RING-5 Documentation

**Reproducible Instrumentation for Numerical Graphics for gem5**

RING-5 turns raw gem5 simulator output into publication-ready figures through an interactive web interface. Parse stats files, transform data, build plots, and export -- all without writing a single script.

---

## Quick Links

| | |
|---|---|
| [Quick Start](Quick-Start) | Get up and running in 5 minutes |
| [Installation](Installation) | Detailed setup instructions |
| [First Analysis](First-Analysis) | Step-by-step walkthrough |
| [Web Interface](Web-Interface) | Dashboard reference |
| [Creating Plots](Creating-Plots) | Visualization options |
| [Architecture](Architecture) | System design for contributors |

---

## For Users

Learn how to parse gem5 stats, transform your data, and create figures for your papers.

- [Parsing gem5 Stats](Parsing-Guide) -- scan variables, configure parsing, generate CSVs
- [Data Transformations](Data-Transformations) -- normalize, aggregate, filter, sort
- [Creating Plots](Creating-Plots) -- all plot types and customization options
- [LaTeX Export](LaTeX-Export-Guide) -- export figures for LaTeX documents
- [Portfolios](Portfolios) -- save and restore complete analysis snapshots

### Plot Types

- [Bar Charts](plots/Bar-Charts)
- [Grouped Stacked Bars](plots/Grouped-Stacked-Bars)
- [Line Plots](plots/Line-Plots)
- [Scatter Plots](plots/Scatter-Plots)
- [Histograms](histogram-plot)

## For Contributors

Understand the architecture and extend RING-5 with new plot types, shapers, or parser features.

- [Development Setup](Development-Setup) -- dev environment and workflow
- [Testing Guide](Testing-Guide) -- writing and running tests
- [Adding Plot Types](Adding-Plot-Types) -- extend the visualization system
- [Adding Shapers](Adding-Shapers) -- create custom data transformations
- [Architecture Overview](Architecture) -- layered design, patterns, and conventions

### API Reference

- [Backend Facade](api/Backend-Facade)
- [Parsing API](api/Parsing-API)
- [Plotting API](api/Plotting-API)
- [Shaper API](api/Shaper-API)

### Architecture Diagrams

- [Full Architecture Diagram](architecture-diagram) -- complete module dependency graph
- [Parsing Architecture](parsing-architecture) -- parser internals
- [Services Architecture](services-architecture) -- services module design

---

## Citation

```bibtex
@software{ring5,
  title  = {RING-5: Reproducible Instrumentation for Numerical Graphics for gem5},
  author = {Nicolas, V.},
  year   = {2026},
  url    = {https://github.com/nikiitin/RING-5}
}
```
