---
layout: default
title: Add a Shaper
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/extension-guides/adding-a-shaper/
---

# Add a shaper

Shapers are stateless, ordered DataFrame transformations in `src/core/services/shapers/`. Each call
returns a new DataFrame and has no Streamlit dependency.

## Implement and register

<!--
`uman~ring5.extension.shaper-registry.documentation~1`

Covers:
- req~ring5.extension.shaper-registry~1

-->

1. Subclass `Shaper` or `UniDfShaper` under `src/core/services/shapers/impl/`. The base constructor
   validates the exact registered implementation and owns a copy of its configuration. Keep
   DataFrame-dependent requirements in `_verify_preconditions` and return a new frame from each call.
2. Add a per-operation `TypedDict` to `src/core/models/shaper_models.py`, with a required exact
   `Literal` `type` field, and include built-ins in `ShaperStepConfig`. Required fields, optional
   defaults, allowed keys and value types are read from this type at runtime.
3. Add a semantic validator in `src/core/services/shapers/definition.py`. It checks relationships
   between already typed fields, without inspecting data or changing configuration values.
4. Register one `ShaperDefinition(identifier, implementation, label, config_type, validate,
   display_order)` in `src/core/services/shapers/factory.py`. Identifiers, implementation classes,
   labels and non-null editor positions are unique. Registration order controls API discovery;
   `display_order` controls the editor order.
5. For a built-in editor, add a component under `src/web/components/shapers/` and wire
   `CONFIG_DISPATCH` in `src/web/pages/ui/shaper_config.py`. Presentation obtains current display
   metadata through `api.shapers.get_shaper_display_names()`; do not copy registry labels into UI maps.

Runtime schemas support `str`, `int`, finite `float`, `bool`, `None`, exact `Literal` values,
unions, typed `list`, string-keyed `dict` and nested `TypedDict` fields. Field-level `Required` and
`NotRequired` determine presence. Registration recursively checks this vocabulary without invoking
the plugin constructor or semantic validator. Unsupported annotations fail with their field path;
recursive schema declarations are supported, while cyclic runtime values are rejected.

Runtime admission bounds the value graph before copying: 100,000 value items, an estimated 256 KiB
of JSON values, 10,000 characters per string and 126 raw container levels. The 100-step and 20-level
SplitApply limits apply independently. Encoded exchange documents also have a 256 KiB file limit.
These bounds prevent a plugin schema or shared value graph from bypassing admission budgets.

## Preserve finalized source contributions

Plot **Finalize** and per-plot analysis recipe pipelines execute with source tracking enabled.
The pipeline publishes its original source, finalized output and contributor relation together.
Implement the relation using `self._source_tracker` when it is present; the scoped
`Shaper._call_with_source_rows` boundary supplies and clears it around the ordinary numerical call.
Do not retain the tracker on cached results or change the public `__call__` signature.

Use the actual numerical operation's row positions: `select` for filters and permutations,
`append_groups` for appended aggregates, `normalize` for original rows plus their baseline,
`combine_groups` for regrouping and `merge_branches` for joined branch results. A row-preserving
operation records the identity positions. The tracker owns bounded DAG nodes in
`src/core/common/source_contributions.py`; no scientific columns carry tracking state. Keep hooks
outside numerical caches so cache hits bind to the current source and execution. Mean, Normalize,
PivotLonger and SplitApply show the existing integration points.

Add the exact implementation class to the reviewed tracked types in `PipelineService._execute`
after reviewing the relation. Registration, a web renderer and inheritance from another shaper do
not grant this capability. Update the independent Distribution policy according to the operation's
coordinate semantics. Tracked execution rejects an unreviewed type explicitly, including nested
SplitApply steps; it never guesses a mapping from final values or replays the current editor draft.

Test identical scientific output with tracking enabled and disabled, exact original row positions,
duplicated caller indexes, missing values, adjacent and nested transformations, input ownership and
TypedTable round trips. Aggregation retains original samples; normalization includes its supporting
baseline. Add the new built-in to `tests/unit/test_source_contributions.py` and cover any new relation
with focused adversarial cases.

## Register an application plugin

Scripts use the public definition contract. A plugin has no editor entry unless its definition
provides an editor position and the application also supplies its web configuration renderer.
Register plugins before admitting saved pipelines that use them. Registered plugins work with
`Session.shape`; using one in a plot's Finalize or per-plot recipe pipeline also requires the reviewed
contribution integration described above. A shaped plugin result passed directly to
`Session.create_plot` establishes that explicit result table as the new plot's source.

```python
from collections.abc import Mapping
from typing import Any, Literal, Required, TypedDict

from ring5.shapers import Shaper, ShaperDefinition, register_shaper

class OffsetConfig(TypedDict, total=False):
    type: Required[Literal["offset"]]
    column: Required[str]
    amount: Required[float]

class Offset(Shaper):
    def __call__(self, frame):
        column = self.params["column"]
        return frame.assign(**{column: frame[column] + self.params["amount"]})

def validate_offset(config: Mapping[str, Any]) -> None:
    if not config["column"]:
        raise ValueError("Offset requires a non-empty column.")

register_shaper(ShaperDefinition("offset", Offset, "Offset", OffsetConfig, validate_offset))
```

Use the registered identifier through the public table pipeline:

```python
import ring5

data = ring5.Table.from_rows([{"ipc": 1.0}])
with ring5.Session() as session:
    shifted = session.shape(data, [{"type": "offset", "column": "ipc", "amount": 0.5}])
    assert shifted.rows() == [{"ipc": 1.5}]
```

Portfolio plot editors preserve JSON-compatible incomplete step drafts. These generic mappings
are editor state; they are validated as runnable operations before execution or standalone pipeline
exchange. A draft is never silently skipped.

Constructor calls may omit the `type` discriminator because the exact class selects the definition.
Serialized pipeline steps require it. A provided discriminator must always match. Unknown keys,
wrong types and unsupported modes fail before execution; inputs are never coerced into the schema.
A subclass needs its own registered definition, rather than inheriting another strategy's contract.
`register_shaper` raises `ring5.errors.PipelineError` for malformed or duplicate definitions.
`Session.shape` reports configuration failures with the top-level step index.

PivotLonger selection filters use canonical decimal-string capture-group keys, including `"0"`
for the whole match. Keys must name groups in the compiled pattern; integer keys and alternate
number spellings are rejected before JSON exchange.

SplitApply validates every nested step through this same registry. One admission permits at most
100 total steps and 20 nested SplitApply levels. Empty sub-pipelines are supported; malformed or
untyped nested steps are rejected.

## Test and verify

Test valid output, input immutability, parameter validation, data preconditions, missing values, and
interaction with adjacent pipeline steps. Assert that `PipelineError` identifies the step at the
public boundary.

```bash
make arch-check
python_venv/bin/mypy src
make test-unit
```

Changing a serialized shaper identifier or configuration shape requires updating all producers and
consumers, current-format round-trip tests, and explicit rejection of the retired contract.
