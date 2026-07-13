---
title: "Settings Pills"
parent: Features
grand_parent: User Guide
nav_order: 2
---

# Settings Pills

## Overview

Settings pills give you fine-grained control over every visual aspect of your plots -- from font sizes and axis formatting to legend placement and color palettes. You access them on the **Manage Plots** page by toggling **Show advanced settings** above a plot's configuration panel.

Settings pills appear as a row of clickable tabs. Selecting a pill expands its configuration panel directly below the pill bar. Three pills are always visible (Layout, Typography, Legends), and four more appear when you enable the advanced toggle (Axes, Data Labels, Colors, Advanced).

Each pill panel produces configuration values that are applied the next time your plot renders. You can adjust settings, click **Refresh**, and immediately see the result in the plot preview.


## Layout

The Layout pill controls the physical dimensions of your figure. These dimensions determine the size of the exported image or PDF, so setting them correctly is important for publication submissions.

### Document Size Preset

You can choose from three size presets:

| Preset | Width | Typical use |
|---|---|---|
| Single Column (~3.5in) | 3.5 inches | One-column figures in IEEE/ACM papers |
| Double Column (~7.0in) | 7.0 inches | Full-width figures spanning both columns |
| Custom | User-defined | Any non-standard width |

When you select Single Column or Double Column, the width field is locked to the preset value. Select Custom to enter an arbitrary width.

### Height

The height field is always editable regardless of the preset. You can set it to any value between 1.0 and 30.0 inches. The default is 3.5 inches.

Margins are managed automatically. RING-5 uses auto-margin mode so that axis labels, titles, and legends are never clipped. You do not need to adjust margins manually.


## Typography

The Typography pill controls font sizes and colors for titles and axis labels. It is organized into two columns: title sizes on the left, and tick label sizes and colors on the right.

### Title Font Sizes

| Setting | Default | Range | What it controls |
|---|---|---|---|
| Plot Title Font Size | 18 | 8--100 | The main title above your plot |
| X-Axis Title Font Size | 14 | 8--100 | The label below the X-axis (e.g., "Benchmark") |
| Y-Axis Title Font Size | 14 | 8--100 | The label beside the Y-axis (e.g., "IPC") |

### Tick Label Sizes and Colors

Tick labels are the values printed along each axis (benchmark names, numeric values, etc.).

| Setting | Default | What it controls |
|---|---|---|
| X-Axis Label Size | 12 | Font size of X-axis tick labels |
| X-Axis Label Color | #444444 | Color of X-axis tick labels |
| Y-Axis Label Size | 12 | Font size of Y-axis tick labels |
| Y-Axis Label Color | #444444 | Color of Y-axis tick labels |

You should see font changes reflected immediately in the plot preview after clicking Refresh. If your tick labels overlap, try reducing the font size or rotating the labels in the Axes pill.


## Legends

The Legends pill controls the appearance and positioning of your plot's legend. For plots with multiple data groupings (such as dual-axis charts), RING-5 supports up to three independent legend levels, each with its own configuration.

### Legend Levels

When you open the Legends pill, you see sub-pills for each available legend level:

- **Primary** -- Always available. Controls the main legend for your color/series grouping.
- **Secondary** -- Appears for dual-axis plots or plots with a secondary grouping.
- **Tertiary** -- Appears for dual-axis plots that also use a numbered X-axis.

Each level has its own independent set of controls, described below.

### Position

| Setting | Default | Description |
|---|---|---|
| X Position | 1.02 (primary), 1.0 (others) | Horizontal position. Values greater than 1.0 place the legend outside the plot area to the right. |
| Y Position | 1.0 | Vertical position. A value of 1.0 aligns the legend with the top of the plot. |
| Orientation | vertical | Choose vertical (entries stacked) or horizontal (entries in a row). Use horizontal when you want the legend above or below the plot. |

### Appearance

| Setting | Default | Description |
|---|---|---|
| Transparent Background | Off | When enabled, the legend has no background fill. |
| Background Color | #ffffff | Fill color behind the legend (hidden when transparency is on). |
| Border Color | #000000 | Color of the border around the legend box. |
| Border Width | 0 | Width of the border in pixels. Set to 0 to hide the border. |
| Text Color | #000000 | Color of the legend entry labels. |
| Font Size | 12 | Size of the legend entry labels. |

### Legend Title

You can add a title above the legend entries by typing text into the **Legend Title** field. You can also set the title's font color and font size (default 14) independently of the entry labels.

### Sizing and Spacing

| Setting | Default | Description |
|---|---|---|
| Columns | 0 | Number of columns. Set to 0 for automatic layout. |
| Item Spacing (px) | 10 | Vertical space between legend entries. |
| Column Spacing | 0.5 | Horizontal space between columns when using multi-column layout. |
| Stripe Length (px) | 30 | Width of the color swatch next to each entry. |
| Stripe-Text Gap | 0.3 | Space between the color swatch and the label text. |

### Heatmap Colorbar

When your plot type is a heatmap, the Legends pill switches to colorbar controls instead of a traditional legend. You can set the colorbar title, choose between automatic or manual value range, configure the number of ticks, tick decimal places, tick rotation, and tick side (left or right).


## Axes

The Axes pill is an advanced setting (hidden by default). It provides detailed control over axis lines, tick marks, grid lines, and axis ranges. The pill uses sub-pills to separate X-axis, Y-Left, and Y-Right configurations.

### X-Axis

| Setting | Default | Description |
|---|---|---|
| Show Grid | Off | Display vertical grid lines at each tick mark. |
| Label Rotation | -45 | Angle of X-axis tick labels in degrees. Use -45 or -90 for long benchmark names. |
| Show Tick Marks | Off | Display small tick marks along the axis. |
| Tick Side | bottom | Place tick marks on the bottom or top of the axis. |
| Grid Dash Style | solid | Style of grid lines: solid, dash, dot, dashdot, or longdash. Only visible when tick marks are enabled. |
| Tick Label Distance | 5.0 px | Padding between tick marks and their labels. |

### X-Axis Lines

You can independently control the bottom and top axis lines:

| Setting | Default | Description |
|---|---|---|
| Bottom Axis Line Width | 1.0 px | Thickness of the bottom axis line. |
| Bottom Axis Line Color | #444444 | Color of the bottom axis line. |
| Top Axis Line Width | 0.0 px | Thickness of the top line. Set to 0 to hide it. |
| Top Axis Line Color | #444444 | Color of the top line. |

### Numbered X-Axis

For plots with many categories, you can replace long text labels with sequential numbers. Toggle **Use Numbered X-Axis** and then select which modes to activate:

- **Numbers** -- Replaces category labels with numeric indices (1, 2, 3, ...).
- **Number legend** -- Adds a separate legend mapping each number back to its original label.

This is particularly useful for bar charts comparing many benchmarks where full names would overlap.

### Y-Axis (Left and Right)

The Y-Left sub-pill is always available. The Y-Right sub-pill appears only for dual-axis plots.

| Setting | Default (Left) | Description |
|---|---|---|
| Show Grid | On (Left), Off (Right) | Display horizontal grid lines. |
| Label Rotation | 0 | Angle of Y-axis tick labels. |
| Y Step Size | 0 (auto) | Fixed interval between Y-axis ticks. Set to 0 for automatic spacing. |
| Show Tick Marks | Off | Display tick marks along the Y-axis. |
| Tick Side | left | Place tick marks on the left or right side. |
| Grid Dash Style | solid | Style of grid lines (solid, dash, dot, dashdot, longdash). |
| Title Standoff | -1 (auto) | Distance between the Y-axis title and the axis. |
| Title Vertical Shift | 0 | Vertical offset of the Y-axis title. This setting applies to Matplotlib exports only. |
| Axis Line Width | 1.0 px | Thickness of the left/right axis line. |
| Axis Line Color | #444444 | Color of the axis line. |

For the primary Y-axis, you can also configure the right-side axis line independently (width and color), even when you are not using dual-axis mode. Set the right axis line width to 0 to hide it.

### Group Labels

The Group Labels sub-pill appears only for grouped stacked bar charts. It controls the positioning of group category labels below the X-axis.

| Setting | Default | Description |
|---|---|---|
| Label-to-Axis Distance | -0.15 | Vertical offset of group labels from the axis. More negative values move labels further down. |
| Alternate Group Labels | On | Stagger labels between two rows to prevent overlap. |
| Alt. Label Row Spacing | 0.05 | Vertical space between the two alternating label rows. |

### Ordering

Within the X-axis sub-pill, you can find expandable sections for reordering and renaming items. Depending on your plot configuration, the following reorder lists may appear:

- **Reorder and Rename X-axis Labels** -- Change the display order and names of categories on the X-axis.
- **Reorder and Rename Groups** -- Rearrange group categories in grouped bar charts.
- **Reorder and Rename Legend Items** -- Control the order of items in the legend.
- **Reorder and Rename Stacked Series** -- Change the stacking order in stacked bar charts.
- **Reorder and Rename Facets** -- Adjust the order of faceted sub-plots.

Each list allows drag-and-drop reordering and inline text editing for renaming.


## Data Labels

The Data Labels pill is an advanced setting. It lets you display numeric values directly on your bars, points, or heatmap cells.

### Enabling Data Labels

Toggle **Show Values** to turn data labels on. When this toggle is off, no other data label controls are visible. You should see numeric annotations appear on your plot elements after enabling this setting and refreshing.

### Formatting

Once data labels are enabled, the following controls appear:

| Setting | Default | Description |
|---|---|---|
| Color Mode | auto | How label colors are chosen: auto (engine decides), contrast (picks a readable color against the background), or custom (you pick a specific color). |
| Custom Color | #000000 | The label color when Color Mode is set to custom. |
| Font Size | 10 | Size of the data label text. |
| Rotation | 0 | Angle of the labels in degrees. Not available for heatmaps. |
| Position | auto | Where labels appear relative to the bar or point: auto, inside, or outside. Not available for heatmaps. |
| Anchor | auto | Text anchor point: auto, start, middle, or end. Not available for heatmaps. |
| Number Format | .2f | Python format string controlling decimal places (e.g., ".2f" for two decimals, ".0f" for integers, ".4g" for significant figures). |

### Display Logic

You can filter which values get a label rather than labeling every data point:

| Setting | Default | Description |
|---|---|---|
| Display Logic | all | Show labels for: all values, only values above a threshold, or only values below a threshold. |
| Threshold Value | 0.0 | The cutoff value when using above/below logic. |

### Size Constraint

The **Size Constraint** setting (default: none) controls whether labels are hidden when they would not fit inside their bar. This is useful for stacked bar charts where small segments would produce overlapping labels.

### Heatmap Totals

When your plot type is a heatmap, an additional section lets you display row or column totals:

| Setting | Default | Description |
|---|---|---|
| Show Totals | Off | Add a summary row or column with aggregated values. |
| Position | right | Where to place the totals: right or bottom. |
| Aggregation | mean | How to aggregate: mean, sum, min, or max. |


## Colors

The Colors pill is an advanced setting. It controls the color palette, per-series color overrides, and background colors.

### Palette Selection

Choose a color palette from the dropdown. The default palette is **wong**, which is colorblind-safe. Palettes marked with a checkmark in the dropdown are verified as colorblind-accessible. A color swatch preview appears below the dropdown so you can see the palette colors before applying them.

### Per-Series Color Overrides

Below the palette selector, each data series in your plot is listed with its assigned color. For each series, you can:

1. View the **original color** assigned by the palette (shown as a disabled color picker).
2. Pick a **custom color** using the adjacent color picker.
3. Check the **Override** checkbox to apply your custom color instead of the palette color.
4. Click the **Rewind** button to reset the series back to the palette default.

When you change the palette, all non-overridden series update to the new palette's colors. Overridden series keep your custom color.

### Per-Series Visual Styles

Depending on the plot type, additional per-series controls appear alongside the color pickers:

- **Bar charts**: A pattern selector lets you add fill patterns (diagonal lines, crosshatch, dots, etc.) to distinguish series in grayscale printing.
- **Line charts**: Controls for marker symbol (circle, square, diamond, triangle, cross, x), marker size (0--50, default 8), and line width (1--20, default 2).
- **Scatter plots**: Same controls as line charts.

### Backgrounds and Grid

| Setting | Default | Description |
|---|---|---|
| Transparent Background | Off | Remove all background fill. Useful for overlaying figures on poster or slide backgrounds. |
| Plot Background | #ffffff | Fill color of the plot area (inside the axes). Hidden when transparency is on. |
| Paper Background | #ffffff | Fill color of the area outside the axes (around the plot). Hidden when transparency is on. |
| Grid Color | #e5e5e5 | Color of grid lines. |
| Axis Line/Tick Color | #444444 | Default color for axis lines and tick marks. |
| Axis Line Width | 1.0 px | Default width for axis lines. |

### Bar Stripes

For bar chart types (except grouped stacked), you can enable **Bar Stripes** to add alternating background shading behind groups of bars. This can improve readability for charts with many categories.

### Heatmap Color Scale

When your plot type is a heatmap, a **Reverse Color Scale** checkbox appears. Enabling it inverts the color mapping so that high values use the start of the scale and low values use the end.


## Advanced

The Advanced pill is an advanced setting that collects several specialized controls: error bars, download format, reference lines, shapes, and engine configuration.

### General Options

| Setting | Default | Description |
|---|---|---|
| Show Error Bars | Off | Display error bars on data points, if error data is available in your dataset. |
| Default Download Format | html | The file format used when you click the download button: html (interactive), png, svg, or pdf. |
| Download Scale | 1 | Resolution multiplier for raster exports. Use 2 or 3 for high-DPI publication figures. |
| Enable Interactive Editing | Off | Allow click-and-drag editing of plot elements in the Plotly preview. |

### Reference Line

You can add a horizontal reference line to mark a meaningful threshold (for example, a baseline IPC of 1.0 or a performance target).

1. Toggle **Show reference line** to On.
2. Set the **Y position** to the value where the line should appear.
3. Choose a **line color** (default: red), **line width** (default: 1.5), and **line style** (solid, dash, dot, dashdot, or longdash).

You should see a horizontal line drawn across the plot at the specified Y value after refreshing.

### Shapes and Annotations

The Shapes sub-section lets you add geometric annotations to your plot for highlighting specific regions.

To add a shape:

1. Select the **Shape Type** (rectangle or line).
2. Enter the coordinates: x0, y0 (start point) and x1, y1 (end point). For rectangles, these define opposite corners. For lines, they define the endpoints.
3. Choose a **color** and **line width**.
4. Click **Add Shape**.

You should see the shape appear on your plot. Each added shape is listed below the form with a Delete button for removal.

### Engine Controls

The engine sub-section provides rendering-engine-specific options. The controls that appear depend on which engine is currently selected for the plot.

**When using Plotly (interactive):**

| Setting | Default | Description |
|---|---|---|
| Hover Mode | x unified | How tooltips behave on hover: x unified (all series at the same X value), closest (nearest point only), or disabled. |

**When using Matplotlib (publication-quality):**

| Setting | Default | Description |
|---|---|---|
| Extra LaTeX Preamble | (empty) | Additional LaTeX packages or commands to include in the preamble. Useful if your labels use special symbols. |
| TeX System | xelatex | The LaTeX engine to use for text rendering: xelatex (recommended, supports Unicode) or pdflatex (legacy). |

For more details on switching between rendering engines, see the Dual Engine feature page.


## Progressive Disclosure

RING-5 uses a two-level disclosure model to keep the interface manageable.

**Level 1 -- Basic vs. Advanced pills.** By default, you see only three pills: Layout, Typography, and Legends. These cover the most common styling needs. Toggle **Show advanced settings** to reveal four additional pills: Axes, Data Labels, Colors, and Advanced. Most users need the advanced pills only when preparing final figures for publication.

**Level 2 -- Within-pill disclosure.** Several pills hide secondary controls until you activate a primary toggle. For example, the Data Labels pill shows only the "Show Values" toggle until you turn it on, at which point all formatting controls appear. Similarly, Axes grid dash style options appear only after you enable tick marks. This keeps each panel focused on the controls that are currently relevant.

Start with the basic pills to set your figure dimensions, font sizes, and legend placement. Expand into the advanced pills when you need to fine-tune axis formatting, add data labels, customize individual series colors, or configure reference lines and export settings.
