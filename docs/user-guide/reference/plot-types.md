---
layout: default
title: Plot Types
parent: Reference
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/reference/plot-types/
redirect_from:
  - /user-guide/features/plot-types/
---

# Plot types

Choose a plot type from the relationship in the processed table. The registry shown in **Plot type**
is authoritative; scripts can inspect the same identifiers:

```python
import ring5

print(ring5.available_plot_types())
```

## Selection guide

| Relationship | Starting point | Data requirement |
| --- | --- | --- |
| One numeric measure by category | `bar` | Categorical X and numeric Y |
| Configurations side by side | `grouped_bar` | X, group, and numeric Y |
| Components of a total | `stacked_bar` | X and numeric component columns |
| Components nested within comparisons | `grouped_stacked_bar` | Major and minor groups plus stack columns |
| Trend over an ordered value | `line` | Ordered X and numeric Y |
| Relationship between numeric measures | `scatter` | Numeric X and Y |
| Distribution of observations | `histogram` | Numeric observations |
| Matrix of values | `heatmap` | Row, column, and numeric value mappings |
| Bars with a distinct right-axis measure | `dual_axis_bar_dot` | Bar mapping and right-axis dot mapping |

These are task descriptions, not a frozen registry inventory. Extensions can register additional
identifiers.

## Common checks

- Finalize the shaper pipeline before mapping columns.
- Keep categorical order explicit when lexical order would change the claim.
- Use a stacked plot only when segments share a meaningful total.
- Label dual axes with units and use visually distinct series encodings.
- Do not use a line merely to connect unrelated categories.
- Inspect error-bar source columns after reduction or normalization.

All plot implementations construct engine-independent traces and can be rendered through Plotly or
Matplotlib. Backend-specific spacing can still differ, so inspect the target engine before export.
