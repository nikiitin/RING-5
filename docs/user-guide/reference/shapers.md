---
layout: default
title: Shapers
parent: Reference
grand_parent: User Guide
nav_order: 2
permalink: /user-guide/reference/shapers/
redirect_from:
  - /user-guide/features/shapers/
---

# Shapers

Shapers form an ordered, per-plot pipeline. Each step receives the previous step's output and returns
a new DataFrame. The **Add transformation** selector lists the registered display names.

Use selectors to keep columns, rows, items, group cardinalities, or groups matching predicates. Use
sort to establish category order. Use normalize and mean for comparison statistics. Use pivot
operations to change table shape, transformer or derive-column operations for computed values, and
split-apply when a transformation must run independently by group.

## Pipeline rules

1. State the required input columns for each step.
2. Order steps by dependency, not by convenience.
3. Preview after every step and check row count, column names, missing values, and baseline rows.
4. Finalize only when the output matches the plot mapping.
5. Preserve serialized identifiers in saved pipelines. Several identifiers use camel case even
   though plot identifiers use snake case.

## Python configuration

`Session.shape` accepts the same discriminated configurations stored in a pipeline:

```python
normalized = session.shape(
    data,
    [
        {
            "type": "normalize",
            "normalizeVars": ["ipc"],
            "normalizerVars": ["ipc"],
            "normalizerColumn": "configuration",
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
            "normalizeSd": True,
        }
    ],
)
```

Normalization requires the baseline row in every group and rejects a zero baseline. When enabled,
companion `.sd` columns are divided by the same baseline. A pipeline failure raises
`ring5.PipelineError` with the failing step index and shaper type where available.

Serialized configuration is validated by each shaper. Use the web configuration form or the typed
models documented in the
[Developer Guide]({{site.baseurl}}/developer-guide/api-reference/models-and-protocols/) rather than
guessing keys for complex steps.

Call `ring5.available_shaper_types()` for the current serialized identifiers. Direct, supported
class imports live in `ring5.shapers`; this includes `ColumnSelector`, `ConditionSelector`,
`ItemSelector`, and the group selector variants in addition to the calculation and pivot shapers.
