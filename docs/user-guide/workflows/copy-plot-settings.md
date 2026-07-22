---
layout: default
title: Copy Plot Settings and Pipelines
parent: Workflows
grand_parent: User Guide
nav_order: 3.9
permalink: /user-guide/workflows/copy-plot-settings/
---

# Copy plot settings and pipelines

<!--
`uman~ring5.plots.copy-settings-pipeline.documentation~1`

Covers:
- req~ring5.plots.copy-settings-pipeline~1

-->

Reuse a plot's presentation or data-shaping work without duplicating the whole plot. The copy is
always explicit about its source, destination, and scope; only the current destination plot changes.

On **Manage Plots**, select the destination plot and open **Copy from another plot**. Choose a source
and one of three modes:

- **Selected figure settings** copies only the chosen sections: titles and labels, layout,
  typography, axes and ordering, legends, colors and series styles, or annotations and data labels.
  Data-column mappings and plot type never change, so presentation can move safely between different
  plot families.
- **Complete plot configuration** replaces every configuration value, including data mappings. The
  source and destination must have the same plot type, and the destination's processed data must
  contain the source columns.
- **Shaping pipeline** replaces the destination's ordered transformations. The destination source
  data must contain the source plot's input columns. After copying, select **Finalize Pipeline for
  Plotting**; RING-5 deliberately clears the stale processed result until that happens.

Select **Copy into current plot** to apply the operation. RING-5 resets stale destination widget
values and reloads the copied configuration. The source is never changed, nested configuration and
pipeline values are deep-copied, and cached figures are invalidated only on the destination.

## Compare before copying

<!--
`uman~ring5.plots.configuration-comparison.documentation~1`

Covers:
- req~ring5.plots.configuration-comparison~1

-->

Choosing a source automatically compares its configuration with the current destination before the
copy controls. The summary shows how many fields match and lists every difference side by side:

- **Changed** means both plots define the setting with different values.
- **Added by source** means a complete replacement introduces the setting.
- **Removed by source** means the setting exists only on the current destination and a complete
  replacement removes it.

Differences are grouped into titles and labels, layout, typography, axes, legends, colors,
annotations, data mappings, and plot-specific settings. Nested settings use paths such as
`series_styles.ipc.color`, so the exact differing leaf remains visible rather than collapsing an
entire style object into one opaque change.

The panel also states whether a complete replacement is compatible. It disables that operation when
plot types differ or the destination lacks a processed-data column required by the source. Selective
settings and pipeline copies remain available because they have their own safety rules. Comparing is
read-only: neither plot, its cached figure, nor its data changes.

## Copy in Python

```python
result = session.copy_plot_content(
    source_plot,
    destination_plot,
    "settings",
    sections=["labels", "typography", "colors"],
)
print(result.copied_keys)

pipeline_result = session.copy_plot_content(
    source_plot,
    destination_plot,
    "pipeline",
)
print(pipeline_result.requires_finalize)  # True

comparison = session.compare_plot_configurations(source_plot, destination_plot)
for difference in comparison.differences:
    print(difference.section, difference.path, difference.source_value, difference.destination_value)
print(comparison.can_replace, comparison.replacement_reason)
```

The section identifiers are `labels`, `layout`, `typography`, `axes`, `legends`, `colors`, and
`annotations`. `ring5.PlotTransferResult` records what was copied and whether the destination needs
pipeline finalization. Unknown plots, modes, sections, incompatible schemas, and cross-type complete
configuration copies raise `ring5.DataValidationError` without partially changing the destination.
`ring5.PlotConfigurationComparison` and `ring5.ConfigurationDifference` provide the same read-only
comparison to scripts. Unknown or identical plot references also raise `ring5.DataValidationError`.
