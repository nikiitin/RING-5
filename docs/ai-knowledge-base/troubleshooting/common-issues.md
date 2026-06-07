---
title: "Common Issues & Status"
parent: Troubleshooting
grand_parent: AI Knowledge Base
nav_order: 1
---

# Common Issues & Status

> AI-optimized reference. Tables, bullets, code blocks. Verify against current source before acting.

---

## Previously-reported "critical bugs" — ALL RESOLVED / verified-correct

An earlier audit flagged eight "critical bugs". Each was re-verified against the current code and is
**resolved or was a false positive**. Do **not** try to "fix" these — the code is correct.

| Former claim | Verified reality |
|---|---|
| Outlier detection removes top 25% (Q3) instead of IQR | Correct textbook **IQR**: `outlier_service.py` removes rows outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]` (global and grouped). |
| `SimpleCache` "Thread-safe" but no lock | Has `threading.Lock` (`src/core/performance.py`); all get/set/clear/stats are guarded. |
| `CsvPoolService._pool_index` has no lock | Guarded by `_pool_lock` (`src/core/services/data_services/csv_pool_service.py`). |
| `WorkPool` has no `shutdown()` → orphaned pools | `WorkPool` and `PerlWorkerPool` both expose `shutdown()` and register `atexit` cleanup. |
| Zero `plt.close()` → matplotlib leak | `src/web/components/common/chart_display.py` calls `plt.close()`; the connector intentionally doesn't (Streamlit owns the figure). |
| matplotlib Figure in `session_state` (not serializable) | Intentional session-scoped render cache (`plot.{id}.mpl_fig`), never serialized to disk; lifecycle managed with `plt.close()`. |
| `mixer.py` missing None check → crash | Guarded (`if mode is None:` …). |
| Mean NaN handling inconsistent | Consistent: `mean.py` `_safe_gmean`/`_safe_hmean` drop NaN and reject non-positive; arithmetic mean uses pandas (skips NaN). |

For the *current*, genuinely-open (minor) issues, see the **Known issues** section of `/CLAUDE.md` — it is
the maintained source of truth.

---

## Architecture boundaries (enforced)

The layer boundaries are enforced by pre-commit hooks + CI; run `make arch-check` (all checks must pass).
Boundary rules:

```bash
# Each MUST return empty:
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__
```

The previously-claimed "web→parsing direct imports" no longer exist — `grep -rn "src.parsing" src/web/`
returns empty (the web layer reaches parsing only through `ApplicationAPI`).

---

## Pandas patterns

- **Immutable transforms only** — never `inplace=True` (enforced by the `no-inplace-true` hook); shapers
  `.copy()` before mutating.
- All shapers implement `__call__(df) -> df`, so they compose with `.pipe()`.
- Categorical ordering uses `pd.Categorical(ordered=True)` (see `transformer.py`).
- To find redundant `pd.DataFrame(df[...])` wrappers (boolean indexing already returns a DataFrame):
  ```bash
  grep -rn "pd\.DataFrame(df\[" src/ --include="*.py" | grep -v __pycache__
  ```

---

## Modernization opportunities

These are nice-to-haves, not bugs. Find current candidates by grepping rather than trusting a fixed count:

- `@override` decorators on `BasePlot` / `Shaper` / `StatType` subclass methods (Python 3.12+).
- `if/elif` chains convertible to `match`/`case` (e.g. selector/factory dispatch).
- Registry string keys that could become `StrEnum` (shaper factory, strategy factory).

---

## Debugging entry points

- Parsing/async issues → `/.claude/skills/parsing-and-variable-types/SKILL.md`.
- Rendering/figure styling → `/.claude/skills/rendering-figureconfig/SKILL.md`.
- Streamlit/UI/e2e → `/.claude/skills/e2e-streamlit-testing/SKILL.md` and `developer-guide/web/streamlit-best-practices.md`.
- Architecture map → `architecture/system-overview.md`, `architecture/layer-boundaries.md`, and `/CLAUDE.md`.
