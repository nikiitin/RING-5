---
title: "Export & Download"
parent: "WebApp Guide"
nav_order: 5
---

<!-- trunk-ignore-all(markdownlint/MD025) -->

# Export & Download

RING-5 supports multiple export formats optimized for different use
cases — from quick sharing to camera-ready publication figures.

---

## Download Formats

| Format   | Engine     | Best For                                       |
| -------- | ---------- | ---------------------------------------------- |
| **PNG**  | Plotly     | Quick sharing, slides, web                     |
| **SVG**  | Plotly     | Scalable vector graphics, editing in Inkscape  |
| **HTML** | Plotly     | Interactive figures for supplementary material |
| **PDF**  | Matplotlib | Camera-ready publication figures               |
| **PGF**  | Matplotlib | Direct LaTeX inclusion (`\input{figure.pgf}`)  |

### Plotly Exports (PNG, SVG, HTML)

Available from the interactive plot toolbar (top-right corner of any
Plotly chart) or via the **Download** section below the chart.

- **PNG**: Rasterized at the current figure dimensions
- **SVG**: Vector format, ideal for post-processing
- **HTML**: Self-contained interactive file — recipients can hover, zoom,
  and pan without RING-5

### Matplotlib Exports (PDF, PGF)

Switch the rendering engine to **Matplotlib** to unlock these formats.
Matplotlib renders text using LaTeX, producing publication-quality
typography that matches your paper's font.

- **PDF**: Standard vector format accepted by all conferences
- **PGF**: Native LaTeX graphics — include directly with
  `\input{figure.pgf}` for perfect font consistency

---

## Rendering Engine Comparison

| Feature              | Plotly                      | Matplotlib               |
| -------------------- | --------------------------- | ------------------------ |
| Interactive preview  | ✅ Hover, zoom, pan         | ❌ Static image          |
| LaTeX text rendering | ❌                          | ✅ Full LaTeX support    |
| Export formats       | PNG, SVG, HTML              | PDF, PGF                 |
| Best workflow stage  | Exploration & configuration | Final publication export |

**Recommended workflow**:

1. Design your chart interactively in **Plotly** mode
2. Switch to **Matplotlib** for the final export
3. Both engines read the same configuration — no settings are lost

---

## Publication Tips

### Conference Requirements

Most top-tier architecture venues (ISCA, MICRO, ASPLOS) require:

- Vector format (PDF preferred)
- Matching document fonts (use PGF for automatic consistency)
- Specific column widths (set figure Width in Layout settings)

### Getting Crisp Text

1. In **Typography** pill, set font sizes to match your paper
   (typically 8–10 pt for tick labels, 10–12 pt for axis titles)
2. Switch to **Matplotlib** engine
3. Download as **PGF** and include in your LaTeX document

### Common Sizes

| Venue Column Type | Typical Width   | Layout Width Setting |
| ----------------- | --------------- | -------------------- |
| Single column     | 3.3 in (252 pt) | ~504 px at 2×        |
| Double column     | 7.0 in (504 pt) | ~1008 px at 2×       |

---

## Portfolios — Save and Reload

If you need to revisit a figure later, save your entire session as a
**Portfolio** (see [Portfolios](../Portfolios.md)). Portfolios preserve:

- Data source configuration
- All shaper pipelines
- Plot settings and visual configuration
- Series colors and ordering

---

## Next Steps

- **Adjust settings before export**: [Plot Settings](Plot-Settings.md)
- **Save your session**: [Portfolios](../Portfolios.md)
- **Return to overview**: [WebApp Guide](../Web-Interface.md)
