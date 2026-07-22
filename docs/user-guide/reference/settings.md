---
layout: default
title: Figure Settings
parent: Reference
grand_parent: User Guide
nav_order: 3
permalink: /user-guide/reference/settings/
redirect_from:
  - /user-guide/features/settings/
---

# Figure settings

Settings change figure presentation after a plot maps processed columns. **Layout**, **Themes**,
**Typography**, and **Legends** are always visible. **Show advanced settings** reveals **Axes**,
**Data Labels**, **Colors**, and **Advanced**.

| Section | Use it for |
| --- | --- |
| Layout | Physical or preview dimensions and automatic margins |
| Themes | Coherent built-ins plus customized theme import and export |
| Typography | Title, axis-title, and tick-label sizes and colors |
| Legends | Visibility, placement, orientation, labels, and spacing |
| Axes | Ranges, scales, ticks, grids, label rotation, and axis-specific controls |
| Data Labels | Values drawn on marks, numeric format, placement, and thresholds |
| Colors | Palettes, per-series overrides, backgrounds, grid styling, and supported patterns |
| Advanced | Reference shapes, error bars, default download configuration, and engine controls |

Plot-specific controls appear with the basic mapping or inside the relevant section. A setting can
be unavailable when it does not apply to the active plot type or engine.

## Setting reference

### Progressive disclosure

<!--
`uman~ring5.figure.advanced-disclosure.documentation~1`

Covers:
- req~ring5.figure.advanced-disclosure~1

-->

Layout, Themes, Typography, and Legends remain available in the basic settings view. **Show
advanced settings** adds Axes, Data Labels, Colors, and Advanced without changing the saved plot
configuration by itself.

### Layout

<!--
`uman~ring5.figure.layout.documentation~1`

Covers:
- req~ring5.figure.layout~1

-->

Choose a single-column, double-column, or custom publication width and set the height in inches.
RING-5 derives the Plotly preview dimensions at 100 pixels per inch and uses automatic zero margins.

### Reuse a figure theme

<!--
`uman~ring5.figure.theme-presets.documentation~1`

Covers:
- req~ring5.figure.theme-presets~1

-->

Open **Themes**, choose a profile, review its description and canvas size, then select **Apply
theme**. The built-ins are starting points with consistent dimensions, typography, surfaces,
palette, legend treatment, and accessible mark defaults:

| Theme | Intended use |
| --- | --- |
| Publication paper | Compact double-column print figures |
| Presentation slide | A 16:9 canvas with large text and marks |
| Dashboard panel | Balanced screen dimensions for repeated panels |
| Dark background | Dark surfaces, light text, visible grids, and a contrast-checked palette |

Applying a theme changes appearance keys only. X/Y mappings, grouping, filters, annotations,
plot-specific meaning, and processed data are retained. The chart refreshes once even when
auto-refresh is off. Existing per-series overrides remain deliberate customizations.

After applying a starting point, adjust **Layout**, **Typography**, **Legends**, **Axes**, or
**Colors**. Return to **Themes**, enter a **Theme name**, and select **Download current theme**.
This exports a JSON file containing only portable appearance settings; it never contains column names,
filters, data, or per-series identities. To reuse it, choose the file under **Theme JSON**, review
the imported name and description, and select **Apply imported theme**. Imports accept one
versioned RING-5 theme object up to 256 KiB and reject unsupported fields, invalid colors, unsafe
dimensions, and unknown palettes before changing the plot.

The same workflow is available to scripts:

```python
import ring5

with ring5.Session() as session:
    custom = session.customize_figure_theme(
        "paper",
        {"title_font_size": 20, "height": 450},
        name="Lab paper",
    )
    payload = session.export_figure_theme(custom)
    restored = session.import_figure_theme(payload)
    config = session.apply_figure_theme(
        {"x": "phase", "y": "ipc", "color": "variant"},
        restored,
        "bar",
    )
```

### Typography

<!--
`uman~ring5.figure.typography.documentation~1`

Covers:
- req~ring5.figure.typography~1

-->

The web controls set title, axis-title, and tick-label sizes and tick colors. The typed Python figure
configuration additionally carries a global font family; legend and data-label typography are set
in their own sections.

### Axes

<!--
`uman~ring5.figure.axes.documentation~1`

Covers:
- req~ring5.figure.axes~1

-->

Configure axis titles, explicit ranges, tick steps and angles, tick marks, grids, axis lines, and
axis-title placement. Applicable dual-axis plots expose the same controls for the right axis.

### Legends

<!--
`uman~ring5.figure.legends.documentation~1`

Covers:
- req~ring5.figure.legends~1

-->

Primary, secondary, and numbered legends have independent visibility, position, orientation,
anchors, column sizing, font, background, border, marker, and spacing settings when the plot type
provides those legend tiers.

### Colors

<!--
`uman~ring5.figure.colors.documentation~1`

Covers:
- req~ring5.figure.colors~1

-->

Choose a named palette or explicit per-series colors. Colorblind-safe palettes are identified in
the selector. Background, grid, axis, and transparent paper or plot colors are stored with the plot.

### Accessible figure themes

<!--
`uman~ring5.figure.accessible-themes.documentation~1`

Covers:
- req~ring5.figure.accessible-themes~1

-->

In **Manage Plots**, turn on **Show advanced settings**, open **Colors**, and enable
**Accessible Theme**. On first activation, RING-5 selects **RING-5 Accessible**, a
color-vision-safe palette whose marks meet a 3:1 contrast target on the default white plot
background. The theme also supplies dark text, readable font-size defaults, visible mark borders,
marker symbols for line and scatter series, and hatch patterns for bar series. Those redundant
symbols and patterns ensure that readers do not have to distinguish series by color alone. The same
encodings are used by Plotly and Matplotlib.

The **Accessibility Check** immediately reports whether the effective settings pass. It checks the
palette's color-vision-safe designation, mark-to-background contrast of at least 3:1, text contrast
of at least 4.5:1, essential text below 10 pt, and non-color encodings when the figure has multiple
series. A green result means those concrete checks passed; it is not a claim that every reader or
assistive technology can interpret the final figure. If a custom palette, background, or text color
breaks a check, the panel lists the affected component, measured ratio where available, and the
action needed.
For a multi-series plot without a verified redundant encoding, or for more than eight series, the
check fails instead of claiming coverage that the rendered marks do not provide.

Scripts can apply and inspect the same profile before rendering:

```python
import ring5

with ring5.Session() as session:
    config = session.apply_accessible_theme(
        {"x": "phase", "y": "ipc", "color": "variant"},
        "line",
    )
    report = session.audit_figure_accessibility(config, "line", series_count=2)
    if not report.passed:
        print(report.to_frame())
```

### Data labels

<!--
`uman~ring5.figure.data-labels.documentation~1`

Covers:
- req~ring5.figure.data-labels~1

-->

Enable formatted values on supported marks and configure color mode, font size, rotation, position,
anchor, numeric format, threshold condition, and the uniform-size constraint.

### Reference lines

<!--
`uman~ring5.figure.reference-lines.documentation~1`

Covers:
- req~ring5.figure.reference-lines~1

-->

Horizontal reference lines have an enabled state, numeric position, color, width, dash style, and
label. A normalized baseline is represented by a line at one.

### Ordering and renaming

<!--
`uman~ring5.figure.ordering-renaming.documentation~1`

Covers:
- req~ring5.figure.ordering-renaming~1

-->

Applicable plots store display-only order and label mappings for X categories, groups, legend
items, stack series, Y metrics, and heatmap facets. These settings do not rewrite processed data.

### Stack totals

<!--
`uman~ring5.figure.stack-totals.documentation~1`

Covers:
- req~ring5.figure.stack-totals~1

-->

Stacked plots can label stack totals with a format, visibility threshold, position, anchor,
typography, offset, and rotation.

### Heatmap summaries

<!--
`uman~ring5.figure.heatmap-summary-controls.documentation~1`

Covers:
- req~ring5.figure.heatmap-summary-controls~1

-->

Heatmaps can add a total row or column, reverse the palette direction, and limit formatted cell
labels to values above or below a threshold. Missing cells use configurable display text.

### Interactive editing

<!--
`uman~ring5.figure.interactive-editing.documentation~1`

Covers:
- req~ring5.figure.interactive-editing~1

-->

Plotly relayout events persist supported zoom and pan ranges, legend positions and anchors, and an
edited primary legend title into plot configuration.

### Alternate category shading

<!--
`uman~ring5.figure.alternate-category-shading.documentation~1`

Covers:
- req~ring5.figure.alternate-category-shading~1

-->

Grouped and grouped-stacked bars can shade alternating major categories with a chosen background
color. This works alongside vertical separators and the optional extra gap before an isolated final
category.

### Series styling

<!--
`uman~ring5.figure.series-styling.documentation~1`

Covers:
- req~ring5.figure.series-styling~1

-->

Where a plot type supports them, per-series overrides set color, display name, bar pattern, marker
symbol and size, line width, opacity, and borders. **Rewind** returns a series to its current palette
color.

## Working method

1. Fix data mapping and category order first.
2. Set final dimensions before tuning fonts and legends.
3. Use units in axis titles and explicit ratio direction for normalized values.
4. Refresh after changes when **Auto-refresh** is disabled.
5. Inspect both the rendered target engine and the exported file.

Interactive Plotly edits such as moving a legend can feed supported relayout changes back into plot
state. Do not rely on an unpersisted browser-only adjustment for a saved portfolio or script.

For headless plots, `ring5.FigureSpec` provides typed common settings. Use its `extra` mapping only
for renderer configuration that is covered by tests and stable for the intended workflow.
