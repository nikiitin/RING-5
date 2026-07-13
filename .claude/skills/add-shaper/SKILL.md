---
name: add-shaper
description: Add a new data-transformation shaper to RING-5's pipeline (subclass Shaper, add a discriminated-union TypedDict config, register in ShaperFactory with a camelCase key, add the UI config). Use when the user wants a new transform/shaper/pipeline step.
---

# Add a new shaper

Shapers are the no-code transform steps. They are **stateless, immutable, composable**: each takes a
DataFrame and returns a *new* DataFrame (`result = data.copy()` first; never `inplace=True`). They
live entirely in Layer B (`src/core/services/shapers/`) — no Streamlit there.

**Best starting move:** copy the closest existing impl in
`src/core/services/shapers/impl/` (e.g. `sort.py`, `normalize.py`, `mean.py`) and adapt.

## Steps

1. **Implement** — `src/core/services/shapers/impl/<name>.py`:
   ```python
   from src.core.services.shapers.shaper import Shaper        # or UniDfShaper for single-frame ops

   class MyShaper(Shaper):
       def _verify_params(self) -> bool:        # static validation of self params (ctor-time)
           ...
       def _verify_preconditions(self, df: pd.DataFrame) -> bool:   # data-dependent validation
           ...
       def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
           result = df.copy()
           # ... transform ...
           return result
   ```
   The shaper is constructed with its config dict: `shaper_class(dict(params))`. NaN-handling
   convention: mirror `impl/mean.py`'s `_safe_gmean`/`_safe_hmean` (dropna, reject non-positive,
   return `np.nan` on edge cases) if doing aggregation.

2. **Typed config** — add a `MyShaperConfig(BaseShaperConfig)` `TypedDict` to
   `src/core/models/shaper_models.py`, and add it to the `ShaperStepConfig` union. The `type`
   field is the discriminator.

3. **Register** in `src/core/services/shapers/factory.py`:
   - add to `ShaperFactory._registry` with a **camelCase** key (e.g. `"myShaper"`);
   - add a human label to `_display_names`.

4. **Validation** — if it needs extra checks, extend `src/core/services/shapers/validation.py`.

5. **UI config** — add `src/web/components/shapers/<name>_config.py` rendering the widgets and
   returning the config dict; wire it into `src/web/pages/ui/shaper_config.py` /
   `selector_transformer_configs.py` dispatch. Per-step unique keys: `f"{prefix}_{field}_{shaper_id}"`.

6. **Tests** — unit in `tests/unit/` (transform correctness + both `_verify_*` paths), plus a
   pipeline/integration test if it interacts with other steps. Import path is
   `src.core.services.shapers.impl.<name>` (NOT `src.web...`).

## Rules & gotchas
- Immutable always (`.copy()`), no `inplace=True`, no bare `except`.
- One transform per shaper (atomic + composable). Shapers run via `pipeline_service.py` which
  fingerprint-caches results — keep `__call__` pure (no hidden state).
- Display names have a single source of truth (`ShaperFactory._display_names`) — don't duplicate them.
- Verify after: `make arch-check && ./python_venv/bin/mypy src/ && make test-unit`.
