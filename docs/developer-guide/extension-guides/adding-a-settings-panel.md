---
layout: default
title: Add a Settings Panel
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 6
permalink: /developer-guide/extension-guides/adding-a-settings-panel/
---

# Add a settings panel

Add a top-level panel only when an existing owner cannot express the setting. Ticks and grids belong
to **Axes**; font sizes and text colors belong to **Typography**; legend behavior belongs to
**Legends**; per-series appearance belongs to **Colors**.

## Implement a visual setting

1. Add the field to the appropriate dataclass under `src/core/models/visualization/`, including
   `to_dict` and `from_dict` behavior.
2. If the field inherits a default, use the existing sentinel convention and add resolution in
   `src/core/services/visualization/config_resolver.py`.
3. Read the persisted flat key in `src/web/rendering/config_builder.py`.
4. Add the widget to its owner under `src/web/components/plotting/settings/`, with a per-plot key.
5. Apply the resolved value in both Plotly and Matplotlib connectors at the same styling stage.
6. Extend `ring5.FigureSpec` when scripts need the setting as supported common configuration.

To add a genuinely new top-level selector, update the declarative sections in
`src/web/pages/ui/plotting/settings_pills.py` and dispatch it from the plot configuration UI.

## Test and verify

Cover model round trips, sentinel resolution, builder mapping, widget defaults, and both connectors.
Test the setting with more than one plot type when its owner is shared.

```bash
make arch-check
python_venv/bin/pytest tests/unit -k "config or connector or render" -n 0 --no-cov
```
