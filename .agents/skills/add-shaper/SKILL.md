---
name: add-shaper
description: Add a new data-transformation shaper to RING-5's pipeline (subclass Shaper, add a discriminated-union TypedDict config, register in ShaperFactory with a camelCase key, add the UI config). Use when the user wants a new transform/shaper/pipeline step.
---

# Add a new shaper

Shapers are **stateless and composable**: each takes a DataFrame and returns a *new* DataFrame
without mutating its input. Copy before assigning into an input's cells; never use `inplace=True`.
They live in `src/core/services/shapers/`, without Streamlit dependencies.

**Best starting move:** copy the closest existing impl in
`src/core/services/shapers/impl/` (e.g. `sort.py`, `normalize.py`, `mean.py`) and adapt.

## Steps

1. **Implement** `src/core/services/shapers/impl/<name>.py`, subclassing `Shaper` or
   `UniDfShaper`. The base constructor validates against the exact registered implementation.
   Keep data-dependent requirements in `_verify_preconditions`; `__call__` returns a new frame.
2. **Typed configuration**: define a per-type TypedDict in `src/core/models/shaper_models.py` with
   `type: Required[Literal["myShaper"]]`. Include built-ins in `ShaperStepConfig`. Runtime validation
   derives required/optional fields, exact value types and allowed keys from this schema.
   Supported annotations are JSON scalars, Literal/union, typed list, string-keyed dict, nested
   TypedDict and field-level Required/NotRequired. Registration preflights them recursively.
   Runtime value graphs are bounded and acyclic before schema traversal or ownership copying.
3. **Semantics**: add a data-independent validator in `definition.py` for field relationships.
   Do not duplicate schema validation or defaults in constructors, imports, or UI components.
4. **Register** one `ShaperDefinition(identifier, implementation, label, config_type, validate,
   display_order)` in `factory.py`. Preserve built-in discovery and editor order. IDs, implementations,
   labels and editor positions are unique. Dynamic plugins use the same public definition contract:
   `from ring5.shapers import Shaper, ShaperDefinition, register_shaper`. API-only plugins omit
   `display_order`; a UI entry also requires a web renderer.
5. **UI**: add the component and `CONFIG_DISPATCH` entry. Obtain display metadata through
   `api.shapers.get_shaper_display_names()`, then pass it into presentation components.
6. **Finalized contributors**: implement the exact row relation through `self._source_tracker`
   when it is present. Use the operation's actual selection, group positions, baseline rows or
   branch join; `source_contributions.py` owns the bounded DAG. Record identity positions for a
   row-preserving operation. Place hooks outside numerical caches and let `_call_with_source_rows`
   scope the tracker. Add the exact implementation class to the reviewed tracked types in
   `PipelineService._execute`; factory registration and subclassing do not grant tracked execution.
   Update the Distribution policy separately according to coordinate semantics.
7. **Tests**: verify constructor/factory/import/pipeline agreement, unknown keys, wrong types and
   modes, data preconditions, immutability and adjacent pipeline interactions. SplitApply uses one
   shared 100-step/20-level validation budget. Assert identical scientific output with tracking
   enabled, exact original positions through adjacent/nested transforms, input ownership and typed
   table round trips. Plugin subclasses need their own explicit definition.

`Session.shape` supports registered application plugins. Plot **Finalize** and per-plot analysis
recipe pipelines require reviewed source contributions and reject an unreviewed implementation
explicitly. A web editor entry alone does not make a plugin eligible. Do not infer contributors
from final labels, replay a mutable draft or substitute processed rows for original inputs.

## Rules & gotchas
- Immutable always (`.copy()`), no `inplace=True`, no bare `except`.
- One transform per shaper (atomic + composable). Shapers run via `pipeline_service.py`; Mean and Normalize
  fingerprint-cache their results — keep `__call__` pure (no hidden state).
- Display names have a single source of truth (`ShaperDefinition`) — don't duplicate them.
- Verify after: `make arch-check && ./python_venv/bin/mypy src/ && make test-unit`.
