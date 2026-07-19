---
layout: default
title: Rendering and Export
parent: Reference
grand_parent: User Guide
nav_order: 4
permalink: /user-guide/reference/rendering-export/
redirect_from:
  - /user-guide/features/dual-engine/
  - /user-guide/reference/supported-formats/
---

# Rendering and export

RING-5 builds engine-independent traces, then resolves figure configuration for Plotly or
Matplotlib. Select the engine before opening **Download** because formats depend on the active
renderer.

Plotly settings also select hover behavior: unified X, closest point, X, Y, or disabled. This is a
rendering preference and does not change the mapped data. Static Plotly downloads accept 1×, 2×,
or 3× scale; higher scale increases raster dimensions and generation cost.

| Engine | Format | External requirement | Typical use |
| --- | --- | --- | --- |
| Plotly | HTML | None | Interactive, self-contained figure |
| Plotly | PNG, SVG, PDF | Chrome-family browser through Kaleido | Static export of interactive rendering |
| Matplotlib | PDF, PNG, SVG | None | Static vector or raster figure |
| Matplotlib | PGF | XeLaTeX | LaTeX-native inclusion |

EPS is not supported. PGF does not support raster graphics; the web application falls back to PDF
when a PGF download contains raster content.

## Check the environment

```bash
source python_venv/bin/activate
ring5 doctor
```

`make dev` installs Playwright Chromium for the development environment. `make install-latex`
installs a TeX distribution on supported package managers; `make check-latex` checks the commands
and packages used by PGF tests.

## Export through Python

The figure type determines the engine-specific formats, and the file extension determines the
format when `fmt` is omitted:

```python
figure = session.plot(
    "bar", data=data, config=spec, engine="matplotlib"
)
session.export(figure, "figure.svg", deterministic=True)
```

An unsupported pairing raises `ring5.ExportError`. A missing optional executable raises
`ring5.DependencyMissingError`. `export_bytes` accepts the same format rules without writing a
file.

Plotly uses configured pixel dimensions. Matplotlib uses configured physical dimensions; PDF, PNG,
and SVG apply tight bounding boxes, while PGF preserves the configured figure size for LaTeX input.
Matplotlib advanced settings select XeLaTeX, pdfLaTeX, or LuaLaTeX for supported text rendering.
The web interface does not accept an arbitrary TeX preamble, and RING-5 escapes user-controlled
figure text before TeX-backed export. User-provided number formats are also bounded before they are
applied to labels.
