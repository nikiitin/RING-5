---
title: "Download Guide"
nav_order: 9
---

## Download Guide

Complete guide to downloading publication-quality plots from RING-5.

## Overview

RING-5 uses a **dual-engine architecture** for rendering. Each engine supports different download formats, so the best choice depends on your output target.

### Engine Comparison

| Feature                  | Plotly          | Matplotlib                   |
| ------------------------ | --------------- | ---------------------------- |
| **Interactive preview**  | ✅ Native       | ❌ Static image              |
| **PNG download**         | ✅ via Kaleido  | ✅ via savefig               |
| **SVG download**         | ✅ via Kaleido  | ✅ via savefig               |
| **PDF download**         | ✅ via Kaleido  | ✅ via savefig (LaTeX fonts) |
| **PGF format**           | ❌              | ✅ LaTeX-native              |
| **EPS format**           | ❌              | ✅ via savefig               |
| **HTML download**        | ✅ Native       | ❌                           |
| **LaTeX text rendering** | ❌              | ✅ pdflatex/xelatex          |
| **Best for**             | Web, dashboards | Papers, LaTeX docs           |

### When to Use Each Engine

- **Plotly** (default): Best for interactive exploration, web sharing, and quick PNG/SVG downloads. Uses Kaleido for server-side rendering.
- **Matplotlib**: Best for LaTeX documents, journal submissions, and pixel-perfect control. Supports LaTeX text rendering for perfect font matching.

## Download Formats

### Plotly Formats

| Format | Extension | Use Case                 |
| ------ | --------- | ------------------------ |
| PNG    | `.png`    | Presentations, web       |
| SVG    | `.svg`    | Scalable vector, editing |
| PDF    | `.pdf`    | General documents        |
| HTML   | `.html`   | Interactive sharing      |

### Matplotlib Formats

| Format | Extension | Use Case                                    |
| ------ | --------- | ------------------------------------------- |
| PDF    | `.pdf`    | LaTeX `\\includegraphics` (recommended)     |
| PGF    | `.pgf`    | LaTeX-native `\\input` (inherits doc fonts) |
| EPS    | `.eps`    | Legacy LaTeX compatibility                  |
| PNG    | `.png`    | Presentations, web                          |
| SVG    | `.svg`    | Scalable vector, editing                    |

## Presets for Publication

RING-5 includes journal-specific presets that automatically set dimensions, fonts, and DPI:

- **single_column**: 3.5" wide, 8pt fonts (IEEE/ACM single column)
- **double_column**: 7.0" wide, 8pt fonts (IEEE/ACM double column)
- **nature**: 3.5" wide, 7pt fonts, 600 DPI
- **science**: 3.4" wide, 7pt fonts
- **ieee_trans**: IEEE Transactions format
- **poster**: Large dimensions, 18pt fonts

Select presets via the **Presets** pill in the settings navigation.

## Prerequisites

**Required System Packages**:

```bash
# Basic LaTeX support (PDF/EPS formats):
sudo apt-get install texlive-latex-base texlive-fonts-recommended \
                     texlive-fonts-extra cm-super texlive-latex-extra

# For PGF format support (optional):
sudo apt-get install texlive-xetex

# Automated installation (recommended):
make install-latex
```

**Package Details**:

- `texlive-latex-base`: Core LaTeX engine (pdflatex) + amsmath, amssymb
- `texlive-fonts-recommended`: Standard LaTeX fonts
- `texlive-fonts-extra`: Additional font packages (~629 MB)
- `texlive-latex-extra`: Additional LaTeX packages
- `cm-super`: Type 1 Computer Modern fonts (provides type1ec.sty)
- `texlive-xetex`: XeLaTeX engine (required for PGF format only)

**LaTeX Packages Used by Matplotlib**:
The export automatically includes these LaTeX packages in the preamble:

- `inputenc[utf8]`: UTF-8 input encoding
- `fontenc[T1]`: T1 font encoding (prevents \mathdefault errors)
- `amsmath`: Advanced math typesetting
- `amssymb`: Mathematical symbols

**Important Note**: Avoid Unicode characters (α, β, etc.) in plot titles/labels.
Use LaTeX math mode instead: `$\\alpha$`, `$\\beta$`, etc.

**Verification**:

```bash
latex --version    # Should show TeX Live version
xelatex --version  # Required for PGF format
make check-latex   # Automated verification
```

---

## Quick Start

### 1. Using the Web Interface (Recommended)

**Steps**:

1. Create your plot in RING-5's web interface
2. Configure styling via the **Settings Pills** navigation
3. Choose your rendering engine (Plotly or Matplotlib)
4. Set download format and scale in the **Download** section
5. Click the download button below the plot
6. For batch downloads, use **Download All Plots** in Workspace Management

**Example Workflow**:

```text
1. Load data → Create bar chart
2. Configure styling via pills (Layout, Colors, Legend, etc.)
3. Switch engine to Matplotlib for LaTeX output
4. Select "single_column" preset
5. Set format to PDF, scale to 3x
6. Download → Include in LaTeX document
```

---

### 2. Using the Python API (Advanced)

For programmatic export or custom workflows:

```python
import plotly.graph_objects as go
from src.plotting.export import LaTeXExportService

# Create Plotly figure
fig = go.Figure(
    data=[go.Bar(x=["A", "B", "C"], y=[10, 20, 15])],
    layout={
        "title": "My Chart",
        "showlegend": True,
        "legend": {"x": 0.8, "y": 0.9},  # Custom position
    }
)

# Initialize service
service = LaTeXExportService()

# Export to PDF
result = service.export(fig, preset="single_column", format="pdf")

if result["success"]:
    with open("figure.pdf", "wb") as f:
        f.write(result["data"])
    print(f"Exported {len(result['data'])} bytes")
else:
    print(f"Error: {result['error']}")
```

---

## Export Formats

### PDF (Recommended)

**Use When**: General-purpose export for LaTeX documents

**Advantages**:

- Works everywhere (LaTeX, Word, PowerPoint)
- Self-contained (fonts embedded)
- Vector format (scales to any size)
- Easy to include: `\includegraphics{figure.pdf}`

**LaTeX Usage**:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.48\textwidth]{figure.pdf}
  \caption{My amazing result}
  \label{fig:result}
\end{figure}
```

---

### PGF (LaTeX-Native)

**Use When**: You want LaTeX to render text natively

**Advantages**:

- Text rendered by LaTeX (matches document fonts perfectly)
- Supports LaTeX math in labels: `$\alpha$`, `$\sum_{i=1}^n$`
- Smallest file size (text is source code, not embedded)

**Disadvantages**:

- Requires LaTeX compilation
- Slower to compile
- Harder to preview outside LaTeX

**LaTeX Usage**:

```latex
\usepackage{pgf}

\begin{figure}[htbp]
  \centering
  \input{figure.pgf}  % Note: \input, not \includegraphics
  \caption{My result}
  \label{fig:result}
\end{figure}
```

---

### EPS (Legacy)

**Use When**: Required by old journals/conferences

**Advantages**:

- Universally supported (even ancient TeX systems)
- Vector format

**Disadvantages**:

- Larger file size than PDF
- Outdated (PDF preferred in modern LaTeX)

**LaTeX Usage**:

```latex
\usepackage{graphicx}
\usepackage{epstopdf}  % Auto-converts EPS → PDF

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.48\textwidth]{figure.eps}
  \caption{My result}
  \label{fig:result}
\end{figure}
```

---

## Journal Presets

RING-5 includes presets for common publication formats:

| Preset Name     | Width | Height | Font Size | Use Case                       |
| --------------- | ----- | ------ | --------- | ------------------------------ |
| `single_column` | 3.5"  | 2.625" | 9pt       | Single-column papers (default) |
| `double_column` | 7.0"  | 5.25"  | 10pt      | Double-column spanning figures |
| `nature`        | 3.46" | 2.6"   | 8pt       | Nature journals                |
| `ieee`          | 3.5"  | 2.625" | 8pt       | IEEE conferences/journals      |
| `acm_sigconf`   | 3.33" | 2.5"   | 9pt       | ACM conferences                |
| `presentation`  | 6.0"  | 4.5"   | 12pt      | Slides/presentations           |

**View All Presets**:

```python
service = LaTeXExportService()
presets = service.list_presets()
print(presets)  # ['single_column', 'double_column', ...]
```

**Inspect Preset Details**:

```python
info = service.get_preset_info("single_column")
print(info)
# {
#   'width_inches': 3.5,
#   'height_inches': 2.625,
#   'font_size_base': 9,
#   'font_family': 'serif',
#   'dpi': 300,
#   ...
# }
```

---

## Custom Presets

Create your own preset for specific journal requirements:

```python
from src.plotting.export import LaTeXExportService

custom_preset = {
    "width_inches": 4.0,
    "height_inches": 3.0,
    "font_size_base": 10,
    "font_size_labels": 9,
    "font_size_title": 11,
    "font_size_ticks": 8,
    "font_family": "serif",
    "line_width": 1.5,
    "marker_size": 5.0,
    "dpi": 600,  # High-res for printing
}

service = LaTeXExportService()
result = service.export(fig, preset=custom_preset, format="pdf")
```

---

## Layout Preservation

RING-5 automatically preserves your interactive adjustments:

### Legend Position

**Interactive**: Drag legend to desired location in web UI

**Export**: Legend position preserved in exported file

**Technical**: Uses the layout mapper to extract `legend.x`, `legend.y`, `legend.xanchor`, `legend.yanchor` from Plotly figure

### Axis Ranges (Zoom)

**Interactive**: Zoom/pan plot to focus on region of interest

**Export**: Axis ranges preserved (`xaxis.range`, `yaxis.range`)

**Example**:

```python
# User zooms to [0.5, 2.5] on x-axis in web UI
fig.layout.xaxis.range = [0.5, 2.5]  # Automatically captured

# Exported figure shows only [0.5, 2.5] range
result = service.export(fig, "single_column", "pdf")
```

### Log Scales

**Interactive**: Toggle log scale in web UI

**Export**: Log scale preserved (`xaxis.type="log"`, `yaxis.type="log"`)

### What Is NOT Preserved

RING-5 intelligently **ignores transient UI state** that shouldn't affect the exported figure:

- Plot cache keys (internal implementation details)
- Temporary hover states
- Animation frames

This ensures exported figures match your **final visual intent**, not intermediate UI states.

---

## Troubleshooting

### Error: "File `type1ec.sty` not found"

**Cause**: Missing `cm-super` font package (required for LaTeX text rendering)

**Solution**:

```bash
sudo apt-get install cm-super texlive-fonts-extra
```

**Explanation**: The `type1ec.sty` file is part of the `cm-super` package, which provides Type 1 Computer Modern fonts. This is required for proper LaTeX text rendering in Matplotlib.

---

### Error: "'xelatex' not found"

**Cause**: Missing XeLaTeX engine (required for PGF format only)

**Solution**:

```bash
sudo apt-get install texlive-xetex
```

**Alternative**: Use PDF or EPS format instead of PGF (PDF is recommended for most use cases).

---

### Error: "Cannot export empty figure"

**Cause**: Figure has no data traces, or all traces have empty data arrays

**Solution**: Ensure your figure contains at least one trace with non-empty data:

```python
fig = go.Figure()
fig.add_trace(go.Bar(x=[1, 2, 3], y=[4, 5, 6]))  # ✅ Has data

# ❌ These will fail:
empty_fig = go.Figure()  # No traces
bad_fig = go.Figure(data=[go.Bar(x=[], y=[])])  # Empty data
```

---

### Error: "LaTeX was not able to process..."

**Cause**: Missing LaTeX system packages

**Solution**:

```bash
# Ubuntu/Debian - Complete installation
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-fonts-extra cm-super dvipng

# macOS
brew install --cask mactex

# Verify installation
latex --version
```

---

### Export Succeeds but Figure Looks Wrong

**Check**:

1. **Preset matches journal**: Use correct column width preset
2. **Data visible**: Ensure data points aren't outside axis ranges
3. **Font sizes**: Adjust font*size*\* in custom preset if too small/large
4. **DPI**: Increase `dpi` (default 300) for higher resolution

**Debug**:

```python
result = service.export(fig, preset="single_column", format="pdf")
print(result["metadata"])  # Check what was applied
```

---

### Performance: Export Takes Too Long

**Cause**: LaTeX text rendering is slow for PGF/EPS formats

**Solutions**:

- Use PDF format (faster, no LaTeX required)
- Reduce number of data points (downsample before plotting)
- Disable LaTeX text rendering (future feature)

**Typical Times**:

- PDF: 1-2 seconds
- PGF: 5-10 seconds (LaTeX compilation)
- EPS: 5-10 seconds (LaTeX compilation)

---

## API Reference

### LaTeXExportService

Main API for exporting figures.

#### `export(fig, preset, format="pdf")`

Export Plotly figure to LaTeX-optimized format.

**Parameters**:

- `fig` (plotly.graph_objects.Figure): Figure to export
- `preset` (str | LaTeXPreset): Preset name or custom dict
- `format` (str): Output format - "pdf", "pgf", or "eps"

**Returns**: ExportResult TypedDict:

```python
{
    "success": bool,       # True if export succeeded
    "data": bytes | None,  # Binary data (write to file)
    "format": str,         # Format used ("pdf", "pgf", "eps")
    "error": str | None,   # Error message if failed
    "metadata": dict,      # Export details (dimensions, fonts, etc.)
}
```

**Example**:

```python
service = LaTeXExportService()
result = service.export(fig, "single_column", "pdf")

if result["success"]:
    with open("output.pdf", "wb") as f:
        f.write(result["data"])
```

---

#### `list_presets()`

Get list of available journal presets.

**Returns**: List[str] - Preset names

**Example**:

```python
presets = service.list_presets()
# ['single_column', 'double_column', 'nature', 'ieee', ...]
```

---

#### `get_preset_info(preset_name)`

Get detailed information about a preset.

**Parameters**:

- `preset_name` (str): Name of preset to inspect

**Returns**: LaTeXPreset dict with configuration

**Example**:

```python
info = service.get_preset_info("nature")
print(f"Width: {info['width_inches']} inches")
print(f"DPI: {info['dpi']}")
```

---

## Examples

### Example 1: Export Bar Chart

```python
import plotly.graph_objects as go
from src.plotting.export import LaTeXExportService

# Create bar chart
fig = go.Figure(
    data=[go.Bar(
        x=["Baseline", "Optimized", "Ours"],
        y=[1.0, 1.5, 2.3],
        name="Speedup"
    )],
    layout={
        "title": "Performance Comparison",
        "xaxis": {"title": "Configuration"},
        "yaxis": {"title": "Speedup (×)"},
    }
)

# Export for single-column paper
service = LaTeXExportService()
result = service.export(fig, preset="single_column", format="pdf")

with open("speedup.pdf", "wb") as f:
    f.write(result["data"])
```

---

### Example 2: Export Line Plot with Custom Legend

```python
# Create line plot with custom legend
fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 4, 9], name="Quadratic"))
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3], name="Linear"))

# Position legend at top-right
fig.update_layout(
    legend={"x": 0.8, "y": 0.95, "xanchor": "left", "yanchor": "top"}
)

# Export to PGF for LaTeX
service = LaTeXExportService()
result = service.export(fig, preset="double_column", format="pgf")

with open("growth_comparison.pgf", "w") as f:
    f.write(result["data"].decode("utf-8"))
```

---

### Example 3: Batch Export Multiple Figures

```python
figures = {
    "fig1_throughput": create_throughput_plot(),
    "fig2_latency": create_latency_plot(),
    "fig3_scalability": create_scalability_plot(),
}

service = LaTeXExportService()

for name, fig in figures.items():
    result = service.export(fig, preset="single_column", format="pdf")

    if result["success"]:
        with open(f"{name}.pdf", "wb") as f:
            f.write(result["data"])
        print(f"✓ Exported {name}.pdf ({len(result['data']) / 1024:.1f} KB)")
    else:
        print(f"✗ Failed {name}: {result['error']}")
```

---

## Architecture

The export system uses a **layered architecture**:

```text
┌─────────────────────────────────────┐
│  Web UI (plot_renderer.py)          │  ← Phase 6
│  - Export dialog                    │
│  - Preset/format selection          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  LaTeXExportService                 │  ← Phase 5 (Facade)
│  - export(fig, preset, format)      │
│  - list_presets()                   │
│  - get_preset_info()                │
└──────────────┬──────────────────────┘
               │
               ├───────────┬──────────────┐
               ▼           ▼              ▼
┌──────────────────┐ ┌────────────┐ ┌────────────────┐
│ MatplotlibConverter│ │PresetManager│ │LayoutMapper    │
│ (Phase 3)         │ │(Phase 1-2)  │ │(Phase 2)       │
│ - Plotly→Matplotlib│ │- Load presets│ │- Extract layout│
│ - LaTeX rendering │ │- Validate   │ │- Preserve user │
│ - Export PDF/PGF  │ │             │ │  adjustments   │
└──────────────────┘ └────────────┘ └────────────────┘
```

**Key Components**:

- **LaTeXExportService**: Simple API for users (Facade pattern)
- **MatplotlibConverter**: Converts Plotly → Matplotlib with LaTeX rendering
- **PresetManager**: Loads and validates journal presets
- **LayoutMapper**: Preserves interactive adjustments (legend, zoom, etc.)

---

## Testing

Export functionality is fully tested:

```bash
# Run all export tests
pytest tests/unit/export/ -v

# Run service tests only
pytest tests/unit/export/test_latex_export_service.py -v

# Run converter tests only
pytest tests/unit/export/converters/test_matplotlib_converter.py -v
```

**Test Coverage**:

- Phase 1-2: 23 tests (presets, layout mapper, base converter)
- Phase 3: 27 tests (Matplotlib converter)
- Phase 5: 17 tests (export service)
- **Total**: 67 tests

**Type Checking**:

```bash
mypy src/plotting/export/ --strict  # Must pass
```

---

## Migration from Legacy Export

RING-5 previously used Kaleido for export. This has been **completely removed** in favor of the Matplotlib-based system.

### What Changed

| Feature             | Legacy (Kaleido) | New (Matplotlib)    |
| ------------------- | ---------------- | ------------------- |
| Export formats      | PNG, SVG, PDF    | PDF, PGF, EPS       |
| Dependencies        | Kaleido binary   | Matplotlib + LaTeX  |
| Layout preservation | None             | Full (legend, zoom) |
| Journal presets     | None             | 6+ built-in         |
| Type safety         | Partial          | mypy --strict       |
| Test coverage       | Limited          | 67 comprehensive    |

### Migration Steps

**Old Code**:

```python
# DEPRECATED - DO NOT USE
from src.plotting.export import ExportService
service = ExportService()
service.render_download_button(plot, fig)  # Old API
```

**New Code**:

```python
# Use LaTeXExportService instead
from src.plotting.export import LaTeXExportService
service = LaTeXExportService()
result = service.export(fig, "single_column", "pdf")
```

**UI**: No changes needed - export dialog automatically uses new system

---

## Further Reading

- **[Adding Plot Types](Adding-Plot-Types.md)**: How to add new plot types that work with export
- **[Backend Facade](api/Backend-Facade.md)**: Integration with RING-5 backend
- **[Testing Guide](Testing-Guide.md)**: Writing tests for export functionality
- **Implementation Plan**: `.agent/plans/latex-export-implementation.md` (technical details)

---

## Support

**Questions**: Open an issue on GitHub with the `export` label

**Bug Reports**: Include:

1. Operating system
2. Python version (`python --version`)
3. LaTeX version (`latex --version`)
4. Minimal reproducible example
5. Error message from `result["error"]`

**Feature Requests**: Suggest new presets, formats, or export options
