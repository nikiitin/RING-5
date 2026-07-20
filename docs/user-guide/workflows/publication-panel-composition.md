---
layout: default
title: Compose Publication Panels
parent: Workflows
grand_parent: User Guide
nav_order: 3.6
permalink: /user-guide/workflows/publication-panel-composition/
---

# Compose publication panels

<!--
`uman~ring5.figure.panel-composition.documentation~1`

Covers:
- req~ring5.figure.panel-composition~1

-->

Start with a dashboard containing the plots that belong in one figure. Turn on **Publication
layout** to make the relationship between panels explicit in papers and reports. **Automatic**
panel labels produce `(a)`, `(b)`, `(c)`, and so on in reading order. Choose **Custom** to provide
one label per line, or **None** when the surrounding document already labels the panels. Captions
also use one line per panel; retain an empty line when only some panels need a caption.

The horizontal and vertical gap controls are percentages of the panel canvas. They are stored in
the immutable dashboard specification, so rebuilding or switching between Plotly and Matplotlib
does not silently recalculate them from the panel count. The common figure title and shared legend
remain independent controls: labels identify individual panels, captions explain them, and the
title and legend describe the complete composition.

The same settings are available from Python:

```python
dashboard = session.create_dashboard(
    [ipc, misses],
    title="Performance overview",
    columns=2,
    panel_labels="auto",
    panel_captions=["Measured throughput", "Last-level cache misses"],
    horizontal_spacing=0.05,
    vertical_spacing=0.10,
    shared_legend=True,
)
```

Spacing values are normalized fractions from `0` through `0.2`; for example, `0.05` requests a
five-percent gap. RING-5 rejects a gap that would consume all available panel space rather than
producing a misleading or empty figure.
