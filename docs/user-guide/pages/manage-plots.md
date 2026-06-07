---
title: "Manage Plots"
parent: Page Guides
grand_parent: User Guide
nav_order: 3
redirect_from:
  - /webapp/Creating-Plots/
  - /Creating-Plots/
---

# Manage Plots

The **Manage Plots** page is the core workspace of RING-5. This is where you
create charts from your gem5 simulation data, customize their appearance, apply
data transformations, and export publication-ready figures.

You can work with multiple plots simultaneously and switch between them at any
time. Each plot maintains its own configuration, data pipeline, and rendering
settings independently.

---

## Page Layout at a Glance

The page is organized into several sections, from top to bottom:

1. **Create Plot form** -- enter a name and choose a plot type.
2. **Plot selector pills** -- switch between your existing plots.
3. **Controls row** -- rename, duplicate, delete, and save/load pipelines.
4. **Pipeline editor** -- add data transformation steps before plotting.
5. **Visualization section** -- configure columns, tweak settings, and view the rendered chart.
6. **Download section** -- export your chart in various formats.

---

## Plot Selector

When you have created one or more plots, a row of pill buttons appears near the
top of the page. Each pill displays the name of a plot.

Click any pill to switch to that plot. The entire page updates to show that
plot's configuration, pipeline, and rendered chart.

If no plots exist yet, you will see a warning message: **"No plots yet"**.

### Duplicating a Plot

Click the **Duplicate** button in the controls row to create an exact copy of
the currently selected plot. The duplicate inherits all configuration, pipeline
steps, and styling from the original. This is useful when you want to create a
variation of an existing chart without starting from scratch.

### Deleting a Plot

Click the **Delete** button to remove the currently selected plot. The page
automatically switches to another plot, or shows the "No plots yet" warning if
none remain.

---

## Creating a Plot

The create-plot form sits at the top of the page and contains three elements:

1. **New plot name** -- a text input where you type a descriptive name for your
   chart (for example, "IPC Comparison" or "Cache Miss Rates").
2. **Plot type** -- a selectbox listing the available chart types.
3. **Create Plot** -- a submit button that creates the plot and selects it.

### Available Plot Types

RING-5 provides 9 plot types, organized into three categories:

| Category | Plot Type | Best Used For |
|----------|-----------|---------------|
| **Basic** | Bar Chart | Comparing a single metric across configurations |
| **Basic** | Line Chart | Showing trends across an ordered variable |
| **Basic** | Scatter Plot | Exploring relationships between two numeric variables |
| **Comparison** | Grouped Bar | Comparing metrics across configurations with an inner grouping variable |
| **Comparison** | Stacked Bar | Showing how sub-components contribute to a total |
| **Comparison** | Grouped Stacked Bar | Combining grouping and stacking for complex multi-level comparisons |
| **Comparison** | Dual Axis Bar Dot | Overlaying bars (primary Y-axis) with dots or lines (secondary Y-axis) |
| **Distribution** | Heatmap | Displaying a matrix of values with color intensity |
| **Distribution** | Histogram | Showing the distribution of a numeric variable across bins |

After clicking **Create Plot**, you should see the new plot appear as a selected
pill in the plot selector, and the visualization section below should display
column configuration widgets for your chosen plot type.

---

## Plot Configuration

Once a plot is created, the visualization section appears with configuration
controls. The exact widgets you see depend on the plot type you selected.

### Changing the Plot Type

At the top of the visualization section, there is a **Plot Type** selectbox. You
can change the type of an existing plot at any time. The data pipeline is
preserved, but the column configuration resets to match the new type.

### Common Configuration Pattern

Most plot types follow a similar pattern for column selection:

- **X-axis** -- select the column for horizontal axis categories or values.
- **Y-axis** -- select the column for the vertical axis metric.
- **Color by** (optional) -- select a categorical column to split data into
  color-coded groups.

Below the column selectors, you will find text inputs for:

- **Title** -- the chart title displayed above the plot.
- **X-axis label** -- label for the horizontal axis.
- **Y-axis label** -- label for the vertical axis.

### Plot-Type-Specific Configuration

Each plot type has its own set of configuration widgets. The following sections
describe what you will see for each type.

#### Bar Chart, Line Chart, Scatter Plot

These three basic types share the same configuration layout:

- X-axis column (categorical or numeric)
- Y-axis column (numeric)
- Color by column (optional, categorical)
- Title, X-axis label, Y-axis label

For Line Charts, you can additionally set the line interpolation shape (linear,
spline, step functions) through the Advanced settings.

#### Grouped Bar

- **X-axis** -- the outer category column (e.g., benchmark name).
- **Y-axis** -- the value column.
- **Group by** -- the inner grouping column (e.g., configuration name).

Additional options include X-axis and group filters that let you select which
values to include or exclude.

#### Stacked Bar

- **X-axis** -- the category column.
- **Y columns** -- select multiple numeric columns to stack on top of each other.

You can optionally enable **Show Totals** to display the sum of each stack as a
label above the bars.

#### Grouped Stacked Bar

This is the most feature-rich plot type. It combines grouping with stacking:

- **X-axis** -- the major group column (outer categories).
- **Group by** -- the minor group column (inner sub-groups).
- **Y columns** -- multiple numeric columns to stack on the left Y-axis.

Optional features include:

- **Dual axis** -- enable a secondary Y-axis with its own columns, displayed as
  bars or dots.
- **Numbered X-axis** -- replace long labels with numbers and display a legend
  mapping numbers to names.
- **Group and category filters** for narrowing the displayed data.

#### Dual Axis Bar Dot

- **X-axis** -- the category column.
- **Y-bar** -- the metric rendered as bars on the primary Y-axis.
- **Y-dot** -- the metric rendered as dots (or a connected line) on the
  secondary Y-axis.
- **Color by** (optional) -- group by color.

Through the Advanced settings, you can control dot size, marker symbol, line
width, and whether dots are connected by lines.

#### Heatmap

- **X-axis** -- the column for horizontal categories (e.g., configurations).
- **Metric columns** -- select multiple numeric columns to display as rows in
  the heatmap grid.
- **Facet column** (optional) -- split into multiple side-by-side heatmaps.
- **Aggregation** -- choose how to summarize duplicate entries (mean, sum, min,
  max, median, or first).

#### Histogram

Histograms in RING-5 work with pre-binned data from gem5 output. The columns
must follow the naming convention `variable..low-high`.

- **Histogram variable** -- the base variable name.
- **Group by** (optional) -- a categorical column for grouped histograms.
- **Normalization** -- count, probability, percent, or density.
- **Cumulative** -- toggle to show the cumulative distribution.
- **Bucket size** -- bin width for density normalization.

---

## Shaper Pipeline

The shaper pipeline lets you transform your data before it reaches the chart.
Pipeline steps execute in order, and each step receives the output of the
previous step.

### Adding a Transformation Step

1. Locate the **Add transformation** selectbox in the pipeline editor section.
2. Select a shaper type from the dropdown.
3. Click **Add to Pipeline**.

You should see a new numbered expander appear in the pipeline list (for example,
"1. Sort" or "2. Column Selector").

### Configuring a Step

Click on a pipeline step's expander to expand it and reveal its configuration
widgets. Each shaper type has different options, described below.

### Reordering and Removing Steps

Each pipeline step has three control buttons:

- **Up** -- move the step earlier in the pipeline.
- **Down** -- move the step later in the pipeline.
- **Del** -- remove the step from the pipeline.

### Finalizing the Pipeline

After adding and configuring your pipeline steps, click **Finalize Pipeline for
Plotting**. This executes all steps in order and produces the processed dataset
that your chart will use.

You should see the visualization section update with column options reflecting
the transformed data.

### Available Shaper Types

#### Column Selector

Keeps only the columns you specify and drops everything else. This is one of the
most commonly used shapers -- gem5 output files often contain hundreds of
columns, and a Column Selector helps you reduce clutter early in the pipeline.

- **Select columns** -- a multiselect widget listing all available columns.
- Quick-action buttons: **Select All**, **Clear All**, **Numeric Only**.

#### Sort

Reorders the rows of your data based on a categorical column.

- **Sort by column** -- the column to sort on.
- **Order** -- Ascending or Descending.

#### Mean Calculator

Aggregates rows by computing the mean (or geometric/harmonic mean) of numeric
columns within each group.

- **Group by columns** -- select one or more categorical columns to group by.
- **Calculate mean for** -- select the numeric columns to aggregate.

This is useful when you have multiple simulation runs and want to average the
results per configuration.

#### Normalize

Divides all numeric values by a baseline row, producing relative metrics (e.g.,
speedup over a baseline configuration).

- **Column to normalize** -- the categorical column that identifies the baseline.
- **Normalization method** -- how to select and apply the baseline.

#### Filter

Keeps only the rows that match a condition.

- **Column** -- the column to filter on.
- **Operator** -- the comparison operator (equals, not equals, greater than,
  less than, contains, etc.).
- **Value** -- the threshold or pattern to compare against.

#### Split-Apply (Per-Axis)

A powerful composite shaper that splits data into groups, applies a sub-pipeline
to each group independently, and then recombines the results. This is useful
when you need different transformations for different subsets of your data.

#### Transformer

Converts column values by applying a mathematical transformation.

- **Source column** -- the column to transform.
- **Transformation** -- the operation to apply (e.g., multiply by a scalar).
- **New column name** -- name for the resulting column.

### Saving and Loading Pipelines

You can save a pipeline configuration for reuse across different plots or
sessions:

- Click **Save Pipe** to open the save dialog. Enter a pipeline name and click
  **Save**.
- Click **Load Pipe** to open the load dialog. Select a previously saved
  pipeline from the dropdown and click **Load**.

If no saved pipelines exist, the load dialog displays a warning: **"No saved
pipelines"**.

---

## Settings Pills (Advanced Settings)

Below the column configuration, you will find a row of pill buttons for
fine-grained chart styling. By default, three basic settings pills are visible:

- **Layout** -- chart dimensions.
- **Typography** -- font sizes and colors.
- **Legends** -- legend position, appearance, and sizing.

### Revealing Advanced Settings

Toggle the **Show advanced settings** switch to reveal four additional pills:

- **Axes** -- axis lines, grid, tick marks, and ordering.
- **Data Labels** -- value labels on data points or bars.
- **Colors** -- color palette, per-series overrides, backgrounds.
- **Advanced** -- error bars, reference lines, shapes, engine controls, and
  export settings.

Click any pill to open its configuration panel. Only one settings panel is
active at a time.

### Layout

Controls the overall chart dimensions.

- **Document Size Preset** -- choose "Single Column (~3.5in)" or "Double Column
  (~7.0in)" for standard academic paper widths, or "Custom" for arbitrary sizing.
- **Width (inches)** -- chart width. Locked unless preset is "Custom".
- **Height (inches)** -- chart height. Always editable.

### Typography

Controls font sizes and colors for all text elements.

- Plot title font size
- X-axis and Y-axis title font sizes
- X-axis and Y-axis tick label sizes and colors

### Legends

Controls legend position, appearance, and sizing. Uses nested sub-pills for
multi-legend support:

- **Primary** -- always available. Position (X, Y coordinates), orientation
  (horizontal/vertical), background and border colors, font size and color,
  title text, column count, and item spacing.
- **Secondary** -- available for dual-axis plot types. Controls the second
  legend independently.
- **Tertiary** -- available for grouped stacked bar plots with dual-axis and
  numbered X-axis. Controls the number-mapping legend.

For Heatmap plots, the legend section shows colorbar controls instead (title,
range mode, tick count, decimals).

### Axes

Controls axis lines, grid, tick marks, and label ordering. Uses nested sub-pills
for each axis:

- **X-Axis** -- grid visibility, label rotation (-90 to 90 degrees), tick mark
  style, axis line width and color, and numbered X-axis modes.
- **Y-Left** -- grid visibility, label rotation, step size (0 for auto), tick
  marks, axis line width and color, and Y-axis title positioning.
- **Y-Right** -- same as Y-Left, for the secondary Y-axis (visible only for
  dual-axis plots).
- **Group Labels** -- label distance and alternating layout (visible only for
  Grouped Stacked Bar).

The X-Axis sub-pill also includes an **Ordering** section where you can reorder
and rename X-axis labels, groups, legend items, stacked series, and heatmap
metrics using drag-and-drop reorderable lists.

### Data Labels

Controls whether and how values are displayed directly on the chart.

- **Show Values** -- master toggle. When off, no other widgets are shown.
- **Value Color Mode** -- auto, contrast (for heatmaps), or custom color.
- **Font Size** and **Rotation** -- control label appearance.
- **Position** and **Anchor** -- control where labels are placed relative to
  data points.
- **Number Format** -- Python format string (e.g., ".2f" for two decimal places,
  ".4g" for four significant figures).
- **Display Logic** -- show all values, or only those above/below a threshold.

For Heatmaps, additional options appear: **Show Totals**, **Totals Position**,
and **Totals Aggregation**.

### Colors

Controls the color palette and per-series visual overrides.

- **Palette** -- choose from the built-in palette registry. Colorblind-safe
  palettes are marked with a checkmark. A color swatch preview is displayed
  below the selector.
- **Reverse Color Scale** -- available for Heatmaps only.
- **Series Color Overrides** -- for each data series, you can override the
  assigned color, enable/disable the override, or reset to the palette default.
  Bar plot types also show a pattern selector (hatching patterns like /, \\, x,
  -, |, +, .) for each series. Line and scatter plots show marker symbol,
  marker size, and line width controls.
- **Backgrounds** -- transparent background toggle, plot area and paper (outer)
  background colors, grid color, and axis line color.
- **Bar Stripes** -- toggle alternating stripe shading (bar types only).

### Advanced

Contains miscellaneous settings organized into sub-sections:

- **Show Error Bars** -- display standard deviation error bars (requires `.sd`
  columns in data).
- **Default Download Format** and **Download Scale** -- control the default
  export behavior.
- **Enable Interactive Editing** -- allow dragging annotations and shapes on
  Plotly charts.
- **Reference Line** -- toggle a horizontal reference line at a specified Y
  position, with configurable color, width, and dash style.
- **Shapes/Annotations** -- add geometric shapes (lines, circles, rectangles)
  to the chart with specified coordinates, colors, and widths.
- **Engine Controls** -- settings specific to the active rendering engine (see
  below).

---

## Rendering Engine

RING-5 supports two rendering engines. You switch between them using the engine
selector pills that appear in the visualization section.

### Plotly (Default)

Plotly produces interactive, web-based charts. This is the default engine and is
best suited for data exploration.

Capabilities:

- Zoom, pan, and hover to inspect individual data points.
- Interactive tooltips showing exact values.
- Client-side export via the Plotly toolbar.
- Supports HTML export for sharing interactive charts.

Engine-specific settings (in the Advanced pill):

- **Hover mode** -- controls how tooltips appear ("x unified", "closest", etc.).

### Matplotlib

Matplotlib produces static, publication-quality images. Switch to Matplotlib
when you are preparing figures for a paper or presentation.

Capabilities:

- Pixel-perfect control over all visual elements.
- Native LaTeX text rendering for mathematical notation.
- PGF export for direct inclusion in LaTeX documents.
- Consistent output across platforms.

Engine-specific settings (in the Advanced pill):

- **Extra LaTeX preamble** -- additional LaTeX packages or commands for PGF
  export.
- **TeX system** -- select the LaTeX compiler (xelatex by default).

---

## Chart Visualization

The rendered chart appears in the main content area below the configuration
section. The behavior depends on the active rendering engine.

### Plotly Charts

When using Plotly, the chart renders as an interactive component. You can:

- **Hover** over data points to see tooltips with exact values.
- **Zoom** by clicking and dragging to select a region.
- **Pan** by holding shift and dragging.
- **Reset** the view by double-clicking.
- **Export** directly from the Plotly toolbar in the upper-right corner of the
  chart.

### Matplotlib Charts

When using Matplotlib, the chart renders as a static image. Interaction features
(zoom, pan, hover) are not available. Use the Download section to export the
figure.

### Refreshing the Chart

You have two options for updating the chart after changing settings:

- **Manual refresh** -- click the **Refresh Plot** button to regenerate the
  chart with your current configuration.
- **Auto-refresh** -- toggle the **Auto-refresh** switch to automatically
  regenerate the chart whenever a configuration value changes.

Manual refresh is useful when making several changes at once, since auto-refresh
regenerates the chart after every individual widget interaction.

---

## Export Presets

Above the settings pills, a **Preset** selector lets you apply predefined
publication-quality configurations. Presets encode precise dimensions, font
sizes, and legend spacing for specific venues.

RING-5 ships with 13 presets covering major computer architecture and scientific
venues including IEEE, ACM, ISCA, MICRO, ASPLOS, HPCA, TACO, Nature, Science,
as well as poster and presentation slide formats.

Selecting a preset overlays its settings onto your current configuration. Your
data, colors, and annotations are preserved -- only layout, typography, and
spacing values are updated to match the venue's requirements.

To return to your custom settings, select **none** from the preset pills.

---

## Download and Export

The download section is located below the rendered chart inside a collapsible
expander labeled **Download**. Click on it to expand the download controls.

### Format Options

The available formats depend on the active rendering engine:

| Engine | Available Formats |
|--------|-------------------|
| **Plotly** | HTML, PNG, SVG, PDF |
| **Matplotlib** | PDF, PGF, PNG, SVG |

Select a format using the format pills, then click the **Download** button. The
file is named after your plot with the appropriate extension.

### Format Recommendations

- **HTML** (Plotly only) -- produces a self-contained interactive chart that can
  be opened in any web browser. Good for sharing results with collaborators.
- **PNG** -- raster image suitable for presentations and quick previews. Plotly
  exports at a configurable scale factor for higher resolution.
- **SVG** -- vector format that scales cleanly at any size. Good for web
  publishing and further editing in vector graphics tools.
- **PDF** -- vector format ideal for including in LaTeX documents. Both engines
  support PDF export.
- **PGF** (Matplotlib only) -- native LaTeX vector format. The exported file
  can be included directly in a LaTeX document with `\input{figure.pgf}`, and
  all text will be rendered by your document's LaTeX compiler. This produces the
  most consistent typographic results for academic papers.

### Batch Export

At the bottom of the page, the workspace management section provides additional
export capabilities:

- **Download All** -- export all plots at once to a specified local directory.
- **Force Format** -- override the export format for all plots.
- **Process All Plots in Parallel** -- regenerate all plots before exporting.
- **Save Entire Workspace** -- persist the complete workspace state including
  all plots, pipelines, and configurations.

---

## Tips and Best Practices

**Start simple, then refine.** Begin with a Bar Chart to verify your data looks
correct. Once you are satisfied with the data pipeline, switch to more complex
plot types like Grouped Stacked Bar or Dual Axis.

**Use Column Selector early.** gem5 statistics files can contain hundreds of
columns. Adding a Column Selector as the first pipeline step reduces clutter
and makes column selection much faster in downstream shapers and plot
configuration.

**Finalize before configuring.** Always click **Finalize Pipeline for Plotting**
after making pipeline changes. The column selectors in the visualization section
only reflect the finalized data.

**Use auto-refresh sparingly.** For complex charts (Grouped Stacked Bar with
dual axis, large heatmaps), auto-refresh can slow down your workflow. Toggle to
manual refresh, make all your changes, then click **Refresh Plot** once.

**Switch to Matplotlib for final export.** Plotly is excellent for interactive
exploration, but Matplotlib produces cleaner static output. When you are ready to
generate figures for a paper, switch to Matplotlib and apply an export preset for
your target venue.

**Apply presets last.** Configure your data, columns, and basic styling first.
Then apply a venue preset to set the correct dimensions and typography. Making
further manual adjustments after applying a preset is fine -- the preset values
are just starting points that you can override.

**Use PGF for LaTeX papers.** If your paper is compiled with LaTeX, the PGF
format (Matplotlib engine) gives you the most consistent results. Text in the
figure will match your document's fonts and will be searchable in the final PDF.

**Duplicate before experimenting.** If you want to try a different visualization
approach for the same data, duplicate your existing plot first. This preserves
your working chart while you experiment with the copy.

**Save pipelines for reuse.** If you find yourself applying the same sequence of
transformations across multiple plots, save the pipeline once and load it into
new plots. This is especially useful for normalization and mean-calculation steps
that are common across benchmarks.
