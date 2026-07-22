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

## Shaper behavior

### Mean

<!--
`uman~ring5.shaping.mean.documentation~1`

Covers:
- req~ring5.shaping.mean~1

-->

Appends one summary row per configured group. `arithmean`, `geomean`, and `hmean` select arithmetic,
geometric, and harmonic aggregation. Arithmetic mean rows recompute companion `.sd` values as the
standard error; geometric and harmonic mean rows leave those companions missing.

### Column selector

<!--
`uman~ring5.shaping.column-selector.documentation~1`

Covers:
- req~ring5.shaping.column-selector~1

-->

Retains the configured columns in the exact configured order. A missing column is an error.

### Condition selector

<!--
`uman~ring5.shaping.condition-selector.documentation~1`

Covers:
- req~ring5.shaping.condition-selector~1

-->

Retains rows by equality, literal substring containment, numeric greater-than or less-than
comparison, an inclusive numeric range, or membership in an explicit values list. Legacy comparison
operators remain accepted for serialized configurations.

### Item selector

<!--
`uman~ring5.shaping.item-selector.documentation~1`

Covers:
- req~ring5.shaping.item-selector~1

-->

Retains rows whose configured column exactly matches any selected string. Contains mode instead
accepts rows containing any selected string as a literal substring.

### Group cardinality selector

<!--
`uman~ring5.shaping.group-cardinality-selector.documentation~1`

Covers:
- req~ring5.shaping.group-cardinality-selector~1

-->

Groups by the configured columns, counts distinct values in the target column, and retains complete
groups whose count is equal to, greater than, or less than the configured threshold.

### Group predicate selector

<!--
`uman~ring5.shaping.group-predicate-selector.documentation~1`

Covers:
- req~ring5.shaping.group-predicate-selector~1

-->

Finds the configured baseline row within each group and tests a selected column for zero, missing,
or either condition. The action chooses whether matching groups are retained or removed as a whole.

### Normalize

<!--
`uman~ring5.shaping.normalize.documentation~1`

Covers:
- req~ring5.shaping.normalize~1

-->

Divides selected numeric columns by the configured non-zero baseline within each group. With
`normalizeSd` enabled, matching `.sd` columns are divided by the same baseline.

### Pivot longer

<!--
`uman~ring5.shaping.pivot-longer.documentation~1`

Covers:
- req~ring5.shaping.pivot-longer~1

-->

Melts selected value columns into a name column and value column. An optional bounded pattern can
extract named categories; selection filters can discard unmatched categories or merge their values
under one label.

### Pivot wider

<!--
`uman~ring5.shaping.pivot-wider.documentation~1`

Covers:
- req~ring5.shaping.pivot-wider~1

-->

Uses configured index, names, and values columns to reshape a long table into one column per names
value. Duplicate index/name pairs retain their first value.

### Sort

<!--
`uman~ring5.shaping.sort.documentation~1`

Covers:
- req~ring5.shaping.sort~1

-->

Orders rows by the explicit category order for each configured column. Values absent from a partial
order remain present after the listed values, in their first-seen order.

### Split apply

<!--
`uman~ring5.shaping.split-apply.documentation~1`

Covers:
- req~ring5.shaping.split-apply~1

-->

Partitions the table by join columns, runs a separate nested shaper pipeline for each configured
column group, and merges the results on those join columns.

### Transformer

<!--
`uman~ring5.shaping.transformer.documentation~1`

Covers:
- req~ring5.shaping.transformer~1

-->

Converts one column to scalar, string, or ordered categorical data. Invalid scalar values become
missing; categorical order is taken from the optional configured order.

### Derive column

<!--
`uman~ring5.shaping.derive-column.documentation~1`

Covers:
- req~ring5.shaping.derive-column~1

-->

Creates or replaces a column using a row-wise sum, ratio, scalar arithmetic operation, string
concatenation, or explicit value mapping. The operation returns a new table.
