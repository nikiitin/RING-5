---
layout: default
title: Style Line Charts
parent: Workflows
grand_parent: User Guide
nav_order: 3.7
permalink: /user-guide/workflows/line-styles/
---

# Style line charts

<!--
`uman~ring5.figure.line-styles.documentation~1`

Covers:
- req~ring5.figure.line-styles~1

-->

Create a line chart, turn on **Show advanced settings**, and open **Axes**. Under **Line & marker
style**, choose the complete visual contract for the series:

- **Connector style** offers straight, smooth-spline, step-after, step-before, and two centered-step
  interpolations.
- **Line pattern** offers solid, dashed, dotted, dash-dot, long-dash, and long-dash-dot strokes.
- **Line width** controls the stroke in points.
- **Show point markers** reveals the marker-symbol and marker-size controls.
- **Connect across missing values** draws between the surrounding observations. It is off by default,
  so missing measurements remain visible as an honest break in the line.

Refresh the figure after changing the controls. Plotly and Matplotlib consume the same stored line
trace. Smooth Matplotlib connectors interpolate numeric, date, and categorical coordinates while
retaining markers only at measured observations; repeated or otherwise ambiguous X coordinates fall
back to straight segments instead of inventing an ordering.

The same contract is available from Python:

```python
plot = session.create_plot(
    "line",
    data=data,
    config={
        "x": "sample",
        "y": "throughput",
        "line_shape": "spline",
        "line_dash": "dashdot",
        "line_width": 3.0,
        "show_markers": True,
        "marker_symbol": "diamond",
        "marker_size": 9,
        "connect_gaps": False,
    },
)
```

The public API rejects unknown styles and unsafe sizes before registering a plot. This prevents a
portfolio from containing a line configuration that only one renderer can interpret.
