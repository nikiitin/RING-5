---
layout: default
title: Manage Portfolios
parent: Workflows
grand_parent: User Guide
nav_order: 4
permalink: /user-guide/workflows/portfolios/
redirect_from:
  - /user-guide/features/portfolios/
  - /user-guide/pages/portfolio/
---

# Manage portfolios

A portfolio stores the current table as CSV text together with plot definitions, shaper pipelines,
parser configuration, and operation history. Use it to reopen or batch-render a RING-5 workspace.
Keep original simulator output and analysis code separately; a portfolio is not a substitute for
research data storage.

## Save and restore in the web application

Open **Save/Load Portfolio** and enter a descriptive name under **Save Portfolio**. Saving from the
web application replaces an existing portfolio with the same sanitized name, so check **Manage
Saved Portfolios** before reusing a name.

Under **Load Portfolio**, choose a saved name and select **Load Portfolio**. Restoration is
best-effort: compatible data and plots can load even when another item is invalid. Review every
warning before trusting a restored workspace.

Portfolios are JSON files under the RING-5 application data directory. It defaults to
`.ring5/portfolios/` in the checkout. Set `RING5_DATA_DIR` before starting RING-5 to use an isolated
or backed-up location.

## Save and restore in Python

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    # Create plots before saving.
    session.save_portfolio("paper-a")

with ring5.Session() as session:
    report = session.load_portfolio("paper-a")
    if not report.complete:
        raise RuntimeError(report)
```

`Session.save_portfolio` refuses to overwrite by default. Pass `overwrite=True` only when replacing
the named snapshot is intentional. `load_portfolio` returns a `RestoreReport` with data, plot, and
parse-variable outcomes.

## Render every saved plot

```python
written = ring5.render_portfolio(
    "paper-a",
    "figures/",
    engine="matplotlib",
    fmt="pdf",
)
```

The CLI provides the same batch operation:

```bash
ring5 render paper-a --out-dir figures/ \
  --engine matplotlib --format pdf
```

Rendering defaults to deterministic output, Matplotlib PDF, or Plotly HTML. The command stops with a
typed error when a plot cannot be restored, rendered, or exported.

Use `ring5 upgrade NAME` to migrate and re-save an older portfolio only after a complete restore.
The command refuses to write a partial restore because that would discard skipped content.
