---
layout: default
title: Rendering and Export
parent: Reference
grand_parent: User Guide
nav_order: 4
permalink: /user-guide/reference/rendering-export/
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
| Matplotlib | PGF | Selected TeX compiler | LaTeX-native inclusion |

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

### Interactive source data

<!--
`uman~ring5.export.plotly-html-source-data.documentation~1`

Covers:
- req~ring5.export.plotly-html-source-data~1

-->

HTML downloaded from the web workspace also includes the processed dataframe that produced the
figure. The table works without a server or network connection and supports whole-table search,
column sorting, pagination, and a client-side CSV download. This is the post-pipeline dataframe:
it therefore shows the exact rows and columns available to the plot, not the unprocessed input.

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

For multi-item analysis documents rather than individual figures, use the
[analysis report workflow]({{site.baseurl}}/user-guide/workflows/batch-reports/). Report HTML embeds every asset;
report PDF uses the dependency-free Matplotlib path and includes the same provenance metadata.

## Check the environment

### Matplotlib TeX system

<!--
`uman~ring5.figure.matplotlib-tex-system.documentation~1`

Covers:
- req~ring5.figure.matplotlib-tex-system~1

-->

Matplotlib advanced settings select `xelatex`, `pdflatex`, or `lualatex` for PGF output.
Python exports use the `tex_system` argument, which defaults to `xelatex`:

```python
session.export(figure, "figure.pgf", tex_system="lualatex")
```

The same option applies to `export_bytes` and `export_submit`. Each export uses an empty custom
preamble and escapes literal figure text. Compiler names are exact identifiers; executable paths
and command options are not accepted. XeLaTeX and LuaLaTeX support installed Unicode fonts;
pdfLaTeX uses its TeX font support. See the
[Matplotlib PGF guide](https://matplotlib.org/stable/users/explain/text/pgf.html#choosing-the-tex-system)
for compiler and font requirements.

Use `ring5.doctor(tex_system="lualatex")` to check the selected compiler without running it.
Saved environment metadata records the versions of all three supported compilers when available.

Recipe exports and `render_portfolio` use each saved plot's `tex_system` setting. Direct exports of
a native figure take this option on the export call; they do not read hidden figure metadata.

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
The `tex_system` option selects the compiler for PGF only. PDF, PNG, and SVG exports use
Matplotlib's standard renderers without invoking TeX.

### Safe numeric and TeX formatting

<!--
`uman~ring5.quality.safe-output-formatting.documentation~1`

Covers:
- req~ring5.quality.safe-output-formatting~1

-->

The web interface does not accept an arbitrary TeX preamble, and RING-5 escapes user-controlled
figure text before TeX-backed export. User-provided number formats are also bounded before they are
applied to labels.

The interactive chart loads the JavaScript bundle shipped with the installed Python
Plotly package. It supports Plotly's binary numeric arrays and renders without a CDN
connection. Dashboards and small multiples support Cartesian, polar, and domain
panels; a single panel must use one coordinate family.

Matplotlib exports preserve category alignment, primary and secondary axis stacking,
and configured error bars. Rendering failures raise an error identifying the failed
series. Heatmap cell labels use the mapped palette color and resolved color bounds
to select contrasting text. The configured figure width and height describe the
complete figure, including all heatmap facets.
