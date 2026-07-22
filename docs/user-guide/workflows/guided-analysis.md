---
layout: default
title: Follow a Guided Analysis
parent: Workflows
grand_parent: User Guide
nav_order: 10
permalink: /user-guide/workflows/guided-analysis/
---

# Follow a guided analysis

<!--
`uman~ring5.workspace.guided-analysis.documentation~1`

Covers:
- req~ring5.workspace.guided-analysis~1

-->

The **Guided analysis** panel in the sidebar follows five milestones:

1. Load simulator output or review and accept an uploaded table.
2. Validate that the table has unique text column names and at least one numeric metric.
3. Complete a baseline-to-candidate comparison in **Data Managers > Compare**.
4. Create and render a visualization in **Manage Plots**.
5. Open the plot's **Download** controls and download the required format.

The panel derives its status from the current workspace. It shows one primary next action, a full
text checklist, and direct navigation to the relevant page. Later milestones do not count until
their prerequisites are complete. Normal sidebar navigation and all advanced controls remain
available throughout the workflow.

The export milestone records an actual figure-download action for the current browser session. It
resets with **Clear Data** or **Reset All**; it does not claim that a file reached any external
publication or review system.

## Inspect progress from Python

`Session.guided_analysis_progress()` reports the same ordered contract. Successful comparison,
render, and export calls advance their milestones:

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    progress = session.guided_analysis_progress()
    print(progress.current_stage, progress.percent_complete)
```

The method does not run an operation or restrict access to the rest of the API. Each stage includes
its status, explanatory detail, action label, and corresponding web destination.
