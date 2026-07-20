---
layout: default
title: Build Analysis Reports
parent: Workflows
grand_parent: User Guide
nav_order: 4.2
permalink: /user-guide/workflows/batch-reports/
---

# Build analysis reports

<!--
`uman~ring5.export.batch-reports.documentation~1`

Covers:
- req~ring5.export.batch-reports~1

-->

Open **Save/Load Portfolio**, then expand **Analysis report**. A report keeps the evidence needed to
read a result away from the live workspace:

- selected plots, either as separate figures or one automatically labeled panel composition;
- ordered plain-language narrative sections;
- an optional bounded preview of the current data table;
- the source type and location, data SHA-256 digest, dimensions, parser variables, and operations;
- RING-5, Python, operating-system, dependency, renderer, and external-tool versions.

Choose **HTML** for a self-contained document with embedded figure images and no remote scripts or
assets. Choose **PDF** for a deterministic multi-page artifact containing the same figures, tables,
narrative, provenance, and environment. RING-5 escapes narrative and table text instead of treating
it as executable HTML or LaTeX. If settings or workspace data change after a build, build again
before downloading.

The displayed-row limit is explicit: a truncated table says how many rows are shown out of the
source total. The data digest always covers the complete current table, not only the displayed
preview.

## Build the same report from Python

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    ipc = session.create_plot(
        "bar",
        data=data,
        config={"x": "benchmark", "y": "ipc"},
        name="IPC by benchmark",
    )
    report = session.create_report(
        "CPU performance review",
        [ipc],
        tables={"Selected measurements": data},
        narrative={"Finding": "IPC improved without a latency regression."},
        figure_captions=["Higher is better."],
        table_row_limit=50,
    )
    session.export_report(report, "reports/cpu-review.html")
    session.export_report(report, "reports/cpu-review.pdf")
```

`report_bytes(report, "html")` and `report_bytes(report, "pdf")` return the same deterministic
payloads without writing to disk. A dashboard returned by `create_dashboard` can appear anywhere an
individual plot appears in the report figure list.
