---
title: "Plot Settings"
parent: "WebApp Guide"
nav_order: 4
---

# Plot Settings Reference

Every plot's visual appearance is controlled through **settings pills** —
collapsible tabs grouped by function. This page documents each pill and
the settings it contains.

---

## Layout

Controls figure dimensions and spacing.

| Setting | Description | Default |
|---------|-------------|---------|
| Width / Height | Figure dimensions in pixels | 900 × 500 |
| Top / Bottom / Left / Right Margin | Space around the plot area (px) | Auto |
| Bar Gap | Space between bars in same group | 0.15 |
| Bar Group Gap | Space between groups | 0.1 |
| Horizontal | Flip chart orientation (bars become horizontal) | Off |

---

## Typography

Font sizes and colors only — positioning lives in Axes.

| Setting | Description | Default |
|---------|-------------|---------|
| Title Font Size | Chart title text size (pt) | 16 |
| Title Color | Chart title color | Black |
| X-Axis Label Font Size | Font size for X-axis title | 14 |
| Y-Axis Label Font Size | Font size for Y-axis title | 14 |
| Tick Font Size | Size for axis tick labels | 12 |

---

## Legend

Configure up to three legend levels for complex multi-group charts.

### Primary Legend (`legend_*`)

| Setting | Description | Default |
|---------|-------------|---------|
| Show | Toggle legend visibility | On |
| X / Y Position | Fractional position relative to plot | 0.5 / 1.05 |
| Columns | Number of legend columns | Auto |
| Background Color | Legend box background | Transparent |

### Advanced: Secondary & Tertiary

For grouped-stacked charts, additional legend levels appear:

- **Secondary** (`legend2_*`): Groups within stacks
- **Tertiary** (`legend3_*`): Stack-level labels

Each level has the same position and column controls.

---

## Axes

Axis-specific appearance. Separated into **X-Axis**, **Y-Left**, and
**Y-Right** sub-sections.

### Common to All Axes

| Setting | Description |
|---------|-------------|
| Show Tick Marks | Draw tick lines on the axis |
| Tick Pad | Distance between tick labels and axis |
| Grid Dash Style | Solid, dash, dot, dashdot, longdash |

### X-Axis Specific

| Setting | Description |
|---------|-------------|
| Tick Angle | Rotation of X-axis labels (-90 to 90°) |
| Category Order | Custom ordering of categorical ticks |
| **Group Labels** section | |
| └ Show Group Labels | Display bracket labels below X-axis ticks |
| └ Alternating Groups | Alternate group label positions (stagger) |
| └ Label Spacing | Vertical gap between group label rows |

### Y-Left Axis

| Setting | Description |
|---------|-------------|
| Range (Min / Max) | Fix Y-axis range (auto if empty) |
| Title Standoff | Horizontal distance of title from axis (px) |
| Title V-Shift | Vertical shift of title position |

### Y-Right Axis

Only visible for **Dual Axis** plot types. Same controls as Y-Left.

---

## Colors

Assign explicit colors to data series.

| Setting | Description |
|---------|-------------|
| Color Palette | Predefined palette or custom |
| Per-Series Color | Click a series name to assign a specific hex color |
| Opacity | Series fill opacity (0–1) |

---

## Data Labels

Show numeric values directly on chart elements.

| Setting | Description | Default |
|---------|-------------|---------|
| Show Data Labels | Toggle labels on bars/points | Off |
| Font Size | Label text size (pt) | 10 |
| Position | Inside, outside, auto | Auto |
| Format | Decimal places and number format | `.2f` |

---

## Ordering

Control the display order of series and categories.

| Setting | Description |
|---------|-------------|
| Reorder Series | Drag to rearrange legend and trace order |
| Rename Series | Edit display names without changing data |
| Reorder X-Categories | Custom order for categorical X-axis values |

---

## Reference Line

Add horizontal reference lines for baselines or thresholds.

| Setting | Description |
|---------|-------------|
| Y Value | Where to draw the line |
| Label | Text annotation |
| Line Style | Solid, dashed, dotted |
| Color | Line color |

---

## Shapes

Add geometric annotations (rectangles, lines) to highlight regions.

| Setting | Description |
|---------|-------------|
| Shape Type | Rectangle, line, circle |
| Coordinates | x0, y0, x1, y1 |
| Fill Color / Opacity | Shape appearance |
| Layer | Above or below data traces |

---

## Engine

Switch rendering backend (Plotly vs Matplotlib) without losing settings.
See [Manage Plots](Manage-Plots.md#rendering-engines) for a comparison.

---

## Advanced

Miscellaneous settings that don't fit other pills.

| Setting | Description |
|---------|-------------|
| Plot Background Color | Inner plot area color |
| Paper Background Color | Outer figure background |
| Show Grid Lines | Toggle gridlines for each axis |

---

## Tips

- **Publication workflow**: Configure everything in Plotly (interactive
  preview), then switch to Matplotlib engine for LaTeX-quality PDF/PGF
  export
- **Spacing issues**: Increase margins before reducing font sizes
- **Group Labels** are only available for grouped bar/stacked bar chart
  types
- Colors set per-series override the selected palette

---

## Next Steps

- **Export the configured plot**: [Export & Download](Export-Download.md)
- **Save for later**: [Portfolios](../Portfolios.md)
