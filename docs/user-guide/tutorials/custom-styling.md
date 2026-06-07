---
title: "Tutorial: Custom Styling"
parent: Tutorials
grand_parent: User Guide
nav_order: 5
---

# Tutorial: Custom Styling

This tutorial walks you through advanced plot customization in RING-5. By the end, you will know how to control typography, colors, legends, axes, layout, and reference lines to produce polished, publication-quality figures.

## Prerequisites

Before starting this tutorial, you should have:

- A dataset loaded on the Data Source page.
- At least one plot created on the Manage Plots page.
- The plot rendered and visible on screen.

If you have not yet created a plot, see the Getting Started guide first.

## Accessing the Settings Panels

Every plot in RING-5 has a settings area below the chart preview. Settings are organized into pill-shaped tabs that you click to switch between sections.

By default, you see three basic sections: **Layout**, **Typography**, and **Legends**. To access additional customization options, toggle the **Show advanced settings** switch above the pill bar. You should see four more sections appear: **Axes**, **Data Labels**, **Colors**, and **Advanced**.

Each section controls a distinct aspect of your plot's appearance. Changes take effect immediately in the chart preview.

---

## Step 1: Typography Customization

Click the **Typography** pill to open the font settings panel.

### Chart Title Font Size

Find the **Plot Title Font Size** input. The default is 18 pt. For a publication figure in a single-column layout, try reducing this to 12-14 pt. Type your desired value directly into the number field.

You should see the title text resize in the chart preview immediately.

### Axis Title Font Sizes

Below the title setting, you will find separate controls for **X-Axis Title Font Size** and **Y-Axis Title Font Size**. Both default to 14 pt.

For a compact single-column figure, try setting these to 10-11 pt. Keeping both axes at the same font size produces a balanced appearance.

### Tick Label Sizes and Colors

The right column of the Typography panel controls tick label (axis number) formatting:

- **X-Axis Label Size** and **Y-Axis Label Size** -- default 12 pt. Try 9-10 pt for publication figures.
- **X-Axis Label Color** and **Y-Axis Label Color** -- default `#444444` (dark gray). Click the color swatch to change. Use `#000000` (black) if your venue requires it.

You should see the axis numbers update in size and color as you make changes.

### Tip: Match Your Document

If you are targeting a specific conference, use the export presets (covered later) instead of setting fonts manually. Presets automatically configure typography to match venue requirements.

---

## Step 2: Color Customization

Toggle **Show advanced settings** on (if not already), then click the **Colors** pill.

### Choosing a Color Palette

The **Palette** dropdown at the top lists all available color palettes. The default is **wong**, a colorblind-safe palette widely used in scientific publications. Palettes marked with a checkmark icon are colorblind-safe.

Select a different palette from the list. You should see the chart colors update immediately. A color swatch preview below the dropdown shows the full palette.

### Overriding Individual Series Colors

Below the palette selector, each data series in your plot is listed with its current color. For each series, you can:

1. Click the **Custom Color** picker to choose a different color.
2. Check the **Override** checkbox to apply your custom color instead of the palette color.
3. Click the **Rewind** button to reset to the palette default.

This is useful when a specific series must match a color convention in your paper (for example, always using red for a baseline configuration).

### Background Colors

Scroll down in the Colors panel to find background controls:

- **Transparent Background** -- toggle on for figures destined for slides with colored backgrounds.
- **Plot Background** -- the color of the chart plotting area. Default is white (`#ffffff`).
- **Paper Background** -- the color of the outer margin area. Default is white.

For most publications, leave both backgrounds white. Turn on transparency if you plan to overlay the figure on a poster or slide.

### Grid Color

The **Grid Color** picker controls the color of grid lines (when visible). The default light gray (`#e5e5e5`) works well for most cases.

---

## Step 3: Legend Customization

Click the **Legends** pill to open the legend settings panel.

### Legend Position

The position controls at the top let you place the legend anywhere on the chart:

- **X Position** -- horizontal placement (0.0 = left edge, 1.0 = right edge, values above 1.0 place the legend outside the plot area).
- **Y Position** -- vertical placement (0.0 = bottom, 1.0 = top).
- **Orientation** -- choose `horizontal` for a legend that reads left-to-right, or `vertical` for a top-to-bottom list.

For a top-center horizontal legend (common in bar charts), set X Position to 0.5, Y Position to 1.05, and Orientation to `horizontal`. You should see the legend move above the chart.

### Legend Appearance

Below the position controls, you can customize:

- **Transparent Background** -- removes the legend box background.
- **Background Color** -- the fill color of the legend box.
- **Border Color** and **Border Width** -- control the legend box outline. Set border width to 0 to remove the border entirely.
- **Text Color** and **Font Size** -- control the appearance of legend labels. Default font size is 12 pt.
- **Legend Title** -- an optional title displayed above the legend entries.

### Legend Sizing

The sizing sub-section provides fine-grained control over legend layout:

- **Columns** -- number of columns in the legend (0 = auto). Set to 2 or more for horizontal legends with many entries.
- **Item Spacing** -- vertical gap between entries in pixels.
- **Column Spacing** -- horizontal gap between columns.
- **Stripe Length** -- the width of the color swatch next to each label.

### Multi-Level Legends

If your plot uses dual-axis or numbered X-axis features, the Legends panel shows sub-pills for **Primary**, **Secondary**, and **Tertiary** legends. Click each sub-pill to configure that legend level independently.

---

## Step 4: Axes Customization

Click the **Axes** pill (requires advanced settings toggle). You should see sub-pills for **X-Axis**, **Y-Left**, and optionally **Y-Right** (for dual-axis plots).

### X-Axis Settings

Click the **X-Axis** sub-pill. Key controls include:

- **Show Grid** -- toggle grid lines on the X-axis. Default is off for bar charts.
- **X-axis Label Rotation** -- a slider from -90 to 90 degrees. Default is -45 degrees. Set to 0 for horizontal labels, -90 for vertical.
- **Show X-Axis Tick Marks** -- small marks at each data point along the axis. Toggle on if your figure style requires them.
- **X-Axis Grid Dash Style** -- appears when tick marks are enabled. Choose from `solid`, `dash`, `dot`, and other styles.
- **X-Axis Tick Label Distance** -- padding in pixels between tick marks and labels. Increase if labels overlap the axis line.
- **Bottom/Top Axis Line Width** -- control the thickness of axis border lines. Set top line width to 0 to remove the top border.

### Y-Axis Settings

Click the **Y-Left** sub-pill. Controls mirror the X-axis with additional options:

- **Show Grid** -- default is on for the Y-axis.
- **Y-axis Label Rotation** -- default is 0 (horizontal).
- **Y Step Size** -- set to 0 for automatic tick spacing, or enter a specific value (e.g., 0.5) for precise control.
- **Y-Axis Title Standoff** -- distance between the axis title and the tick labels.
- **Y-Axis Line Width** and **Right Axis Line Width** -- control left and right border lines independently.

### Setting Manual Axis Ranges

To ensure consistent scales across multiple plots (for example, all IPC plots ranging from 0 to 2.0), use the Y Step Size control combined with the shaper pipeline's value range filter.

---

## Step 5: Layout Fine-Tuning

Click the **Layout** pill to adjust the overall figure dimensions.

### Figure Dimensions

- **Document Size Preset** -- quick selection for common widths. Choose **Single Column (~3.5in)** for narrow figures or **Double Column (~7.0in)** for full-width figures. Select **Custom** to enter an arbitrary width.
- **Width (inches)** -- editable only when the preset is set to Custom.
- **Height (inches)** -- always editable. Default is 3.5 inches. Range is 1.0 to 30.0 inches.

You should see the chart preview resize as you adjust dimensions. The chart preview uses a scaled pixel representation of the final output size.

### Margins

RING-5 uses automatic margin calculation by default. The margins adjust to fit your axis labels and legend without clipping. If you need manual control, the export presets provide margin overrides for publication-quality output.

### Background Colors

The background colors in the Colors section (see Step 2) control both the plot area and the outer paper area. Adjust these in the Colors pill, not the Layout pill.

---

## Step 6: Reference Lines

Reference lines are horizontal or vertical lines drawn across the plot at a fixed value. They are commonly used to mark a baseline (for example, a normalized value of 1.0).

### Adding a Reference Line

1. Toggle **Show advanced settings** on.
2. Click the **Advanced** pill.
3. Find the **Reference Line** sub-section.
4. Toggle **Show reference line** on.

You should see a horizontal line appear on your chart.

### Configuring the Reference Line

Once enabled, additional controls appear:

- **Y position** -- the Y-axis value where the line is drawn. Default is 1.0. Set this to your baseline value.
- **Line color** -- default is red (`#FF0000`). Click the swatch to change.
- **Line width** -- a slider controlling thickness. Default is 1.5.
- **Line style** -- choose from `dash`, `solid`, `dot`, and others. Default is `dash`.

For normalized performance data, a dashed line at y=1.0 clearly marks the baseline configuration.

---

## Step 7: Saving Your Styled Plot

After customizing your plot, all settings are automatically stored in the current session. To preserve your work across sessions:

### Export the Figure

1. Scroll to the **Download** section below your chart.
2. Choose an export format using the format pills (PNG, SVG, PDF, or PGF).
3. Click the **Download** button.

All visual customizations -- typography, colors, legends, axes, layout, and reference lines -- are preserved in the exported file.

### Save a Portfolio

To save the complete workspace (including all plot configurations and data), go to the **Portfolio** page and save a snapshot. This stores every setting so you can return to your exact configuration later.

### Use Export Presets

If you are targeting a specific venue (IEEE, ACM, ISCA, MICRO, Nature, etc.), select an export preset from the preset pills above the settings area. Presets automatically override typography, dimensions, and spacing to match the venue's requirements. Your data, colors, and series assignments remain unchanged.

---

## Summary

| Aspect | Settings Section | Key Controls |
|--------|-----------------|--------------|
| Font sizes and colors | Typography | Title size, axis title sizes, tick label sizes and colors |
| Color palette and overrides | Colors (advanced) | Palette selector, per-series color pickers, backgrounds |
| Legend position and style | Legends | X/Y position, orientation, font size, border, columns |
| Axis grid, ticks, borders | Axes (advanced) | Grid toggle, rotation, tick marks, dash style, line widths |
| Figure size | Layout | Width/height presets, custom dimensions |
| Baseline markers | Advanced | Reference line enable, position, color, style |

With these controls, you can adjust every visual aspect of your RING-5 plots to meet the requirements of any publication venue or presentation format.
