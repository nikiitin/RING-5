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
rendering preference and does not change the mapped data. Its mode-bar image control accepts 1×,
2×, or 3× scale; higher scale increases raster dimensions and generation cost.

| Engine | Format | External requirement | Typical use |
| --- | --- | --- | --- |
| Plotly | HTML | None | Interactive, self-contained figure |
| Plotly | PNG, SVG, PDF | Chrome-family browser through Kaleido | Static export of interactive rendering |
| Matplotlib | PDF, PNG, SVG | None | Static vector or raster figure |
| Matplotlib | PGF | XeLaTeX | LaTeX-native inclusion |

EPS is not supported. PGF does not support raster graphics; the web application falls back to PDF
when a PGF download contains raster content.

## Rendering engines

### Plotly rendering

<!--
`uman~ring5.render.plotly.documentation~1`

Covers:
- req~ring5.render.plotly~1

-->

Plotly converts every typed trace to an interactive figure and applies the resolved common figure
configuration. Interactive relayout support is available only in this engine.

### Matplotlib rendering

<!--
`uman~ring5.render.matplotlib.documentation~1`

Covers:
- req~ring5.render.matplotlib~1

-->

Matplotlib draws every registered typed trace as static artists, including secondary axes and
multi-panel heatmaps. Backend-specific text and spacing can differ from Plotly.

### Session engine selection

<!--
`uman~ring5.render.engine-selection.documentation~1`

Covers:
- req~ring5.render.engine-selection~1

-->

The active Plotly or Matplotlib choice is session-scoped. It changes the visible controls, render
cache identity, and available download formats for the active plot.

### Plotly raster scale

<!--
`uman~ring5.export.plotly-scale.documentation~1`

Covers:
- req~ring5.export.plotly-scale~1

-->

The Plotly mode-bar image control accepts a 1×, 2×, or 3× scale. The selected value is passed in
Plotly's `toImageButtonOptions` together with the configured preview dimensions. The separate
Download panel uses its own export defaults.

## Export formats

### Plotly HTML

<!--
`uman~ring5.export.plotly-html.documentation~1`

Covers:
- req~ring5.export.plotly-html~1

-->

HTML export embeds Plotly JavaScript and figure data in a self-contained interactive document. It
does not invoke Chrome or Kaleido.

### Plotly static formats

<!--
`uman~ring5.export.plotly-static.documentation~1`

Covers:
- req~ring5.export.plotly-static~1

-->

PNG, SVG, and PDF export use Kaleido and a Chrome-family browser. Transient browser failures use a
bounded retry; a missing browser is reported immediately as a dependency failure.

### Matplotlib standard formats

<!--
`uman~ring5.export.matplotlib-standard.documentation~1`

Covers:
- req~ring5.export.matplotlib-standard~1

-->

PDF, PNG, and SVG export use the configured physical figure dimensions. PNG also applies the
selected raster DPI.

### Matplotlib PGF

<!--
`uman~ring5.export.matplotlib-pgf.documentation~1`

Covers:
- req~ring5.export.matplotlib-pgf~1

-->

PGF export preserves physical size for LaTeX inclusion and uses the selected TeX system. The web
download reports a visible PDF fallback when raster content prevents PGF serialization.

## Check the environment

### Matplotlib TeX system

<!--
`uman~ring5.figure.matplotlib-tex-system.documentation~1`

Covers:
- req~ring5.figure.matplotlib-tex-system~1

-->

Matplotlib advanced settings select XeLaTeX, pdfLaTeX, or LuaLaTeX for PGF output. The web
application fixes the additional preamble to an empty value because a TeX preamble is executable
input.

### Plotly hover mode

<!--
`uman~ring5.figure.plotly-hovermode.documentation~1`

Covers:
- req~ring5.figure.plotly-hovermode~1

-->

Plotly advanced settings select unified X, closest-point, X, Y, or disabled hover behavior. The
selection is stored in the common figure configuration and applied by the Plotly connector.

```bash
source python_venv/bin/activate
ring5 doctor
```

`make dev` installs Playwright Chromium for the development environment. `make install-latex`
installs a TeX distribution on supported package managers; `make check-latex` checks the commands
and packages used by PGF tests.

## Export through Python

<!--
`uman~ring5.export.public-boundary.documentation~1`

Covers:
- req~ring5.export.public-boundary~1

-->

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
