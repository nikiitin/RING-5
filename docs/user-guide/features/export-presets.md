---
title: "Export Presets"
parent: Features
grand_parent: User Guide
nav_order: 5
---

# Export Presets

## Overview

Export presets apply pre-configured dimensions, font sizes, and layout settings
optimized for specific publication venues. When you select a preset, RING-5
automatically adjusts your plot to meet the submission requirements of that
conference or journal.

Presets handle the tedious details of publication formatting so you can focus on
your data. They set figure width and height in inches, choose appropriate font
families and sizes, configure DPI for raster output, and tune legend spacing --
all in a single click.

RING-5 ships with 13 built-in presets covering major computer architecture
conferences, high-impact journals, and presentation formats.


## How to Apply a Preset

1. Navigate to the **Manage Plots** page.
2. Locate the plot you want to export.
3. Expand the **Download** section below the plot chart.
4. Select a preset from the preset pills displayed at the top of the section.

You should see the preset name highlighted and the plot dimensions update to
match the selected venue format.

When you select a preset, RING-5 overlays the preset settings onto your current
plot configuration. Your data, colors, annotations, and trace styling are
preserved. Only the layout dimensions, typography, axis formatting, legend
spacing, and font family change.

To remove a preset and return to your manual settings, select **None** from the
preset pills.


## Available Presets

RING-5 organizes its 13 presets into four categories: computer architecture
conferences, high-impact journals, IEEE/ACM standards, and presentation formats.

### Computer Architecture Conference Presets

These presets target the major venues in the computer architecture community.
They use serif fonts with a LaTeX monospace preamble to match IEEE/ACM document
styles.

#### MICRO -- IEEE/ACM International Symposium on Microarchitecture

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

#### ISCA -- International Symposium on Computer Architecture

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

#### ASPLOS -- Architectural Support for Programming Languages and Operating Systems

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

#### HPCA -- IEEE International Symposium on High-Performance Computer Architecture

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

### Journal Presets

#### TACO -- ACM Transactions on Architecture and Code Optimization

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

#### Nature

Nature requires a square aspect ratio, Arial font, smaller text, and high DPI
for print quality.

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 3.5 inches  |
| Font family     | Arial       |
| Base font size  | 7 pt        |
| Title font size | 8 pt        |
| Label font size | 7 pt        |
| Tick font size  | 6 pt        |
| Line width      | 0.5 pt      |
| Marker size     | 2.0         |
| DPI             | 600         |

#### Science

Science uses a sans-serif font with compact text and high DPI.

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | sans-serif  |
| Base font size  | 8 pt        |
| Title font size | 9 pt        |
| Label font size | 8 pt        |
| Tick font size  | 7 pt        |
| Line width      | 0.5 pt      |
| Marker size     | 2.0         |
| DPI             | 600         |

### IEEE/ACM Standard Presets

#### IEEE Single Column

Matches IEEE Transactions formatting for single-column figures.

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 10 pt       |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

#### ACM

Matches ACM proceedings formatting with a slightly smaller base font.

| Property        | Value       |
|-----------------|-------------|
| Width           | 3.5 inches  |
| Height          | 2.5 inches  |
| Font family     | serif       |
| Base font size  | 9 pt        |
| Title font size | 10 pt       |
| Label font size | 9 pt        |
| Tick font size  | 8 pt        |
| Line width      | 1.0 pt      |
| Marker size     | 4.0         |
| DPI             | 300         |

### General Layout Presets

#### Single Column

A standard single-column figure with a 16:9 aspect ratio. Suitable for any
two-column paper when you need a compact figure.

| Property        | Value         |
|-----------------|---------------|
| Width           | 3.5 inches    |
| Height          | 1.97 inches   |
| Font family     | serif         |
| Base font size  | 10 pt         |
| DPI             | 300           |

#### Double Column

A full-width figure spanning both columns of a two-column paper. Uses a 4:3
aspect ratio.

| Property        | Value         |
|-----------------|---------------|
| Width           | 7.0 inches    |
| Height          | 5.25 inches   |
| Font family     | serif         |
| Base font size  | 10 pt         |
| DPI             | 300           |

### Presentation Presets

#### Poster

Designed for research posters with large text, thick lines, and generous
dimensions.

| Property        | Value         |
|-----------------|---------------|
| Width           | 10.0 inches   |
| Height          | 7.0 inches    |
| Font family     | sans-serif    |
| Base font size  | 24 pt         |
| Title font size | 28 pt         |
| Label font size | 24 pt         |
| Tick font size  | 20 pt         |
| Line width      | 2.0 pt        |
| Marker size     | 8.0           |
| DPI             | 150           |

#### Slides

Formatted for 16:9 presentation slides with large, readable text.

| Property        | Value         |
|-----------------|---------------|
| Width           | 8.0 inches    |
| Height          | 4.5 inches    |
| Font family     | sans-serif    |
| Base font size  | 18 pt         |
| Title font size | 22 pt         |
| Label font size | 18 pt         |
| Tick font size  | 14 pt         |
| Line width      | 1.5 pt        |
| Marker size     | 6.0           |
| DPI             | 150           |


## Export Formats

After selecting a preset (or without one), you can download your plot in several
formats. The available formats depend on which rendering engine you are using.

### Matplotlib Engine Formats

When using the Matplotlib engine, the following formats are available:

- **PDF** -- Vector format, ideal for LaTeX papers using `\includegraphics{}`.
  Text remains sharp at any zoom level. This is the default format for
  Matplotlib.

- **PGF** -- Native LaTeX vector format. You can include PGF files directly in
  your LaTeX document with `\input{figure.pgf}`. Fonts automatically match
  your document. This is the best option for LaTeX papers.

- **PNG** -- Raster format at the preset DPI (300 for papers, 600 for
  Nature/Science). Good for drafts and quick previews.

- **SVG** -- Scalable vector format. Useful for editing in vector graphics
  tools like Inkscape or Adobe Illustrator.

### Plotly Engine Formats

When using the Plotly engine, the following formats are available:

- **HTML** -- Interactive format with zoom, pan, and hover tooltips. Opens in
  any web browser. This is the default format for Plotly.

- **PNG** -- Raster format exported at 2x scale for sharp rendering.

- **SVG** -- Vector format suitable for web use or further editing.

- **PDF** -- Vector format for static documents.


## Choosing the Right Format

| Use Case                                | Format | Engine     |
|-----------------------------------------|--------|------------|
| LaTeX paper with `\input{}`             | PGF    | Matplotlib |
| LaTeX paper with `\includegraphics{}`   | PDF    | Matplotlib |
| High-DPI journal submission             | PDF    | Matplotlib |
| Interactive web report or presentation  | HTML   | Plotly     |
| Quick preview or draft sharing          | PNG    | Either     |
| Editing in Inkscape or Illustrator      | SVG    | Either     |


## Tips

**Use Matplotlib for final exports.** The Matplotlib engine produces
publication-quality static output with proper LaTeX rendering. Switch to
Matplotlib before applying a preset and exporting your final figures.

**Use PGF for the best LaTeX integration.** PGF files contain native LaTeX
commands, so fonts in your figures automatically match your document. This
avoids font mismatch issues that can occur with PDF or PNG exports.

**Use PNG for quick previews.** When you are iterating on your plot design, PNG
export is fast and universally viewable. Save the high-quality PDF or PGF
export for your final submission.

**Presets work with both engines.** You can apply the same preset whether you
are using Plotly or Matplotlib. The preset adjusts dimensions and typography
identically for both engines, so you can explore interactively with Plotly and
then switch to Matplotlib for the final export.

**Nature and Science presets use 600 DPI.** These journals require higher
resolution than standard conference venues. The preset handles this
automatically, but be aware that PNG files at 600 DPI will be larger.

**Conference presets include a LaTeX monospace font preamble.** The MICRO, ISCA,
ASPLOS, HPCA, TACO, ACM, single column, and double column presets include a
LaTeX preamble that loads the Inconsolata monospace font (`zi4` package). This
matches the monospace font used in typical IEEE/ACM documents.
