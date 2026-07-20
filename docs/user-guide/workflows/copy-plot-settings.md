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
```

The section identifiers are `labels`, `layout`, `typography`, `axes`, `legends`, `colors`, and
`annotations`. `ring5.PlotTransferResult` records what was copied and whether the destination needs
pipeline finalization. Unknown plots, modes, sections, incompatible schemas, and cross-type complete
configuration copies raise `ring5.DataValidationError` without partially changing the destination.
