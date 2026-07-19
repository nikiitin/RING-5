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

Settings change figure presentation after a plot maps processed columns. **Layout**, **Typography**,
and **Legends** are always visible. **Show advanced settings** reveals **Axes**, **Data Labels**,
**Colors**, and **Advanced**.

| Section | Use it for |
| --- | --- |
| Layout | Physical or preview dimensions and automatic margins |
| Typography | Title, axis-title, and tick-label sizes and colors |
| Legends | Visibility, placement, orientation, labels, and spacing |
| Axes | Ranges, scales, ticks, grids, label rotation, and axis-specific controls |
| Data Labels | Values drawn on marks, numeric format, placement, and thresholds |
| Colors | Palettes, per-series overrides, backgrounds, grid styling, and supported patterns |
| Advanced | Reference shapes, error bars, default download configuration, and engine controls |

Plot-specific controls appear with the basic mapping or inside the relevant section. A setting can
be unavailable when it does not apply to the active plot type or engine.

Stacked plots can label stack totals with a format, visibility threshold, position, anchor,
typography, offset, and rotation. Heatmaps can add a total row, reverse the palette direction, and
limit formatted cell labels to values above or below a threshold. These controls are serialized in
the plot configuration and restored with a portfolio.

Grouped and grouped-stacked bars can shade alternating major categories with a chosen background
color. This works alongside vertical separators and the optional extra gap before an isolated final
category.

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
