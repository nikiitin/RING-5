---
layout: default
title: Home
nav_order: 1
permalink: /
---

## RING-5 Documentation

Reproducible Instrumentation for Numerical Graphics for gem5

RING-5 turns raw gem5 simulator output into publication-ready figures through an interactive web
interface. Parse stats files, transform data, build plots, and export -- all without writing a single
script.

---

## Documentation

| Guide | For | Start here |
| ----- | --- | ---------- |
| [User Guide](user-guide/) | Researchers using the app | [Installation](user-guide/getting-started/installation/) · [First Steps](user-guide/getting-started/first-steps/) |
| [Developer Guide](developer-guide/) | Contributors & maintainers | [Architecture Overview](developer-guide/architecture/overview/) · [Development Setup](developer-guide/development/setup/) |
| [Engineering Reference](engineering-reference/) | Maintainer catalogs and task references | [System Overview](engineering-reference/architecture/system-overview/) · [File Locations](engineering-reference/quick-reference/file-locations/) |

### Popular topics

- **Parse gem5 stats** -- [Data Source page](user-guide/pages/data-source/) and
  [Parsing Architecture](developer-guide/parsing/parsing-architecture/)
- **Transform data** -- [Shapers](user-guide/features/shapers/) (normalize, aggregate, filter, sort)
- **Create plots** -- [Plot Types](user-guide/features/plot-types/) and
  [Manage Plots page](user-guide/pages/manage-plots/)
- **Publication export** -- [Publication-ready tutorial](user-guide/tutorials/publication-ready/)
- **Save your work** -- [Portfolios](user-guide/features/portfolios/)
- **Extend RING-5** -- [Adding a plot type](developer-guide/extension-guides/adding-a-plot-type/) ·
  [Adding a shaper](developer-guide/extension-guides/adding-a-shaper/)

> Working in the repo with an AI coding agent? The canonical in-repo guide is
> [`AGENTS.md`](https://github.com/nikiitin/RING-5/blob/main/AGENTS.md) with task recipes under
> `.agents/skills/`.

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
