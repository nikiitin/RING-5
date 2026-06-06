# RING-5 Architecture & Coupling Audit

> Generated Jun 2026. Two-pass audit of all **241 modules / ~39.6k LOC** in `src/`.
> Pass 1 = deterministic AST import-graph (structural coupling). Pass 2 = a 22-subsystem
> multi-agent semantic read (one Opus reader per subsystem, every file read in full), with
> every HIGH/MEDIUM finding adversarially verified by a refute-by-default skeptic.
> 83 agents, ~3.16M tokens. Findings below are reconciled against CLAUDE.md's documented
> contracts and spot-checked against source by the lead.

---

## Verdict

**The MVC / 3-layer split is genuinely well kept.** No HIGH-severity violation survived
verification. The hard boundaries hold line-by-line: **zero** `streamlit` / `session_state` /
`plotly` / `matplotlib` / `kaleido` / `src.web` imports anywhere in `core` or `parsing`, and
**no hard import cycles** (the two real back-edges are deliberately deferred via `TYPE_CHECKING` +
late imports, both commented). The coupling that exists is concentrated in a few identifiable
**seams**, not spread across the codebase.

The real story is three things:
1. Three **dependency-direction** violations the `arch-check` greps can't see (Pass 1).
2. A leaky **"engine-agnostic" rendering contract** — Plotly vocabulary bleeds into Core and into
   supposedly engine-neutral helpers, causing real **dual-engine (matplotlib) inconsistencies**.
3. Inconsistent **defensive-copy / immutability discipline** at the state & service boundaries —
   latent, not yet biting, but contradicting the stated "immutable for reproducibility" intent.

---

## Layer coupling scorecard

| Layer | Modules | Intra-layer edges | Density | Notes |
|-------|--------:|------------------:|--------:|-------|
| Web (Presentation) | 125 | 233 | 1.86 | Largest by LOC (23.7k); reaches Core internals ~2:1 vs. the facade |
| Core (Domain+Data) | 79 | 160 | 2.03 | Densest internally; the most-depended-on layer (`models`) |
| Parsing (Data) | 36 | 60 | 1.67 | Cleanest; one upward dep into Core services |

Cross-layer import edges (top): `WEB→MODELS` 71, `SERVICES→MODELS` 28, `PARSING→MODELS` 21,
`WEB→SERVICES` 17, `WEB→FACADE` 10. The `WEB→SERVICES` (17) **exceeds** `WEB→FACADE` (10): the UI
bypasses `ApplicationAPI` more often than it uses it.

---

## Tier 1 — Structural direction violations (deterministic, Pass 1)

These break the `Web → Core ← Parsing` one-directional rule. The greps miss all three.

| # | Edge | Site | Severity | Note |
|---|------|------|----------|------|
| S1 | **Models → Services** | `core/models/visualization/__init__.py:40-41` | HIGH (cleanliness) | Re-exports `resolve_config`, `resolve_palette`, `get_palette_names`, `is_colorblind_safe` from `services.visualization.*`. Models are documented to "depend on nobody." Near-cycle: `palette_service` imports back into `models.visualization.palettes`. Importing the most-depended-on package drags in the whole `services.visualization` subtree. |
| S2 | **Parsing → Services** | `parsing/gem5/impl/gem5_parser.py:87`, `parsing/parse_service.py:14` | MEDIUM | Layer A imports `PatternIndexService` from Layer B. `parse_service.py` is a self-described back-compat shim "for test `@patch` targets" — production layering shaped by test mocking. |
| S3 | **Facade erosion** | 21 sites; worst: `web/models/plot_protocols.py:31`, `web/pages/plot_adapters.py:41`, `web/pages/ui/plotting/plot_service.py:19` → `core.state.repository_state_manager` | MEDIUM | UI reaches `RepositoryStateManager` and core services directly instead of via `ApplicationAPI`. Stateless helpers (`palette_service`, `config_resolver`) are defensible; the **state-manager** ones are the real leak. |

**Fix for S1/S2:** invert — keep the pure resolver/palette helpers reachable without the model
package re-export (callers import from `services`), and move `PatternIndexService` down to
`parsing` or `models` (it is a low-level index, used by the parser). **S3:** route plot/state
mutations through `ApplicationAPI` (or a `PlotHandle` API) rather than the raw state manager.

---

## Tier 2 — Confirmed semantic issues (verified MEDIUM)

Each survived an adversarial refutation pass and was spot-checked against source.

### M1 — Live plot config mutated in place via shallow copy → state corruption
`src/web/components/plotting/settings/shapes_settings.py:40-138`
The render controller hands the **live** `plot.config` as `saved_config` and only shallow-copies it
(`current_config = saved_config.copy()`). `shapes = saved_config.get("shapes", [])` therefore
returns the **same list** stored in `plot.config`; `shapes.append(...)` / `shape["x0"] = ...` mutate
persisted state *before* the `config_changed = current_config != saved_config` check runs — so the
change-detection can never see its own mutation.
**Fix:** deep-copy `shapes` (and nested `line` dicts) before editing; build and return a new list.

### M2 — Engine-specific legend relabel applied to Plotly only → dual-engine drift
`src/web/controllers/plot/render_controller.py:219-225`
`fig.for_each_trace(lambda t: t.update(name=legend_labels.get(...)))` is a Plotly-`graph_objects`
API. The matplotlib branch (lines 246-257) renders from `plot.last_traces.traces` (the
engine-agnostic traces) which **never received the relabel**. Matplotlib legends silently ignore
`legend_labels`.
**Fix:** apply the original→display name mapping to `TraceConfig.name` before connectors run (or in
both connectors), per `STYLING_PIPELINE_ORDER`.

### M3 — Plotly figure styling hardcoded in a "utils" helper → dual-engine drift
`src/web/pages/ui/plotting/utils/grouped_stacked_bar_helpers.py:235-431`
`update_yaxes` / `add_annotation` / `update_layout(legend2=...)` mutate a raw Plotly `go.Figure`.
Secondary-legend + dual-axis-title styling bypasses `FigureConfig` + the connectors, so the
matplotlib engine gets none of it.
**Fix:** express via `FigureConfig` (`legend2_*` fields + an axis-title/annotation spec) so
`config_resolver` + both connectors apply it; keep the helper emitting engine-agnostic
`TraceConfig`/`FigureConfig` (as `build_right_axis_traces` already does).

### M4 — Pipeline execution engine duplicated in the view layer
`src/web/pages/ui/shaper_config.py:95-167`
`apply_shapers` re-implements the shaper-pipeline loop (iterate configs → validate → `ShaperFactory`
→ pipe DataFrame) that already exists in `PipelineService.process_pipeline`
(`core/services/shapers/pipeline_service.py:140`) and is exposed via `ApplicationAPI.apply_shapers`.
Layer C owns Layer B business logic; the two can drift.
**Fix:** call `api.apply_shapers(...)`; keep only per-step warning rendering in the view.

### M5 — Scan worker downgrades hard failures to "no variables"
`src/parsing/gem5/impl/scanning/gem5_scan_work.py:37-42`
`Gem5StatsScanner.scan_file` is fail-fast (raises on Perl crash / timeout / corrupt JSON). The
worker catches **base `Exception`**, logs a `warning`, and returns `[]`. After
`aggregate_scan_results` merges per-file lists, a crashed scan is indistinguishable from a file that
legitimately had zero variables — a systemic failure (broken regex, wrong path) presents to the user
as "nothing found."
**Fix:** re-raise the fatal conditions (so the future surfaces them), or return a type that
distinguishes "scanned: empty" from "scan failed."

---

## Cross-cutting themes

### A. The "engine-agnostic" rendering contract is leaky (strongest theme)
Plotly is the de-facto engine; its vocabulary leaks across the boundary, and matplotlib silently
diverges. Beyond M2/M3:
- `core/services/visualization/plot_interaction.py:89-211` — Domain service decodes **Plotly relayout
  event keys** (`xaxis.range[0]`, `yaxis.autorange`, `legend2.x`→`legend2_x`) and emits Plotly anchor
  literals. (verified real; skeptic rated LOW — stateless, no import cost)
- `core/models/visualization/trace_build_result.py:29-40` — `shapes` typed as **"Plotly-format shape
  dicts"** in an explicitly engine-agnostic model.
- `core/services/portfolio_migrator.py:57-74` — hardcodes engine name `"plotly"`.
- `web/rendering/widgets/widget_def.py:643-670` — `COLORS_PALETTE` hardcodes Plotly palette names in
  the engine-agnostic widget layer.
**Consequence:** secondary legends, dual-axis titles, and legend relabeling differ between engines.
**Direction:** define neutral intent models (separator/shape, relayout-intent, legend-position) and
translate per-connector.

### B. Domain/data logic concentrated in plot-type view classes
The `web/pages/ui/plotting/types/*.py` classes do pivoting, aggregation (mean/sum/min/max/median),
statistical normalization, and bucket-range parsing inside `create_traces`:
`heatmap_plot.py:27-64,211-301`, `histogram_plot.py:123-183,257-298`, `stacked_bar_plot.py:145-202`,
`dual_axis_bar_dot_plot.py:50-297` (a ~240-line god-method). The skeptic considered these acceptable
**view-prep** (not domain analytics) and refuted them individually — a defensible position. The
residual concern is **duplication + SRP**: the same reshape/ordering/inherit logic is hand-rolled per
type rather than shared via shapers/helpers. Worth a consolidation pass, not a boundary fix.

### C. Inconsistent defensive-copy / immutability discipline (latent)
CLAUDE.md describes repositories as "defensive-copy on read" and models as "immutable … to guarantee
reproducibility." Reality is mixed (each item below was individually refuted as *harmless today / not
a hard rule*, but together they're a latent-mutation risk class):
- State repos mostly return internal mutables **by reference** (`config`/`plot`/`parser_state`/`data`/
  `preview`), while `History`/`Visualization.get_all` copy — and `creation_controller.change_plot_type`
  actually mutates `get_plots()` in place. (`plot_repository.py:43-50`, `config_repository.py:37-152`)
- `get_data()` returns the stored frame by reference though `set_data()` deep-copies — one-sided
  copy-on-write. (`repository_state_manager.py:61-62`)
- Frozen `ScannedVariable.to_dict()/from_dict()` leak the `entries`/`pattern_indices` **lists** by
  reference. (`models/parsing_models.py:56-75`)
- `FigureConfig` is **non-frozen** and mutates its own fields in `__post_init__`. (`figure_config.py:97-201`)
- Selector shapers can return a pandas **view/slice** instead of a copy.
  (`shapers/impl/selector_algorithms/column_selector.py:59-62`)
- `type_mapper.map_scan_result` and `config_aware.post_process` mutate caller dicts in place.
**Direction:** decide whether copy-on-read is a real contract; if yes, make repos uniform and freeze
`FigureConfig`; if no, soften the docstrings. Copy mutable members at model serialization boundaries.

### D. Minor presentation-in-core / sim-specific-in-generic leaks
- `web/components/plotting/config/heatmap_config.py:86` — hardcoded gem5 stat prefix `"l0_ctrl"`
  (and `"benchmark_name"`) in a generic plot config view ("multi-simulator by design").
- `core/application_api.py:205,214` — `is_regex = r"\d+" in name` heuristic in the generic facade
  (skeptic argues `\d+` is part of the cross-layer `ScannedVariable` contract via `pattern_aggregator`
  — defensible).
- `core/services/shapers/factory.py:54-117`, `managers/arithmetic_service.py:18-35` — user-facing
  display labels owned by Domain services (skeptic: intentional single source for labels — defensible).

### E. Dead / duplicate surface
- `core/services/shapers/pipeline_service.py:79-138` — still carries `save/load/list/delete` pipeline
  persistence; CLAUDE.md lists "Pipeline save/load dialogs" as a **removed feature**. No production caller.
- `core/services/config_validation_service.py:29-378` — `ConfigTemplateGenerator` /
  `create_simple_bar_plot_config` appears **test-only / orphaned**.
- `web/models/plot_models.py:94-104` — `ShaperStep` duplicates core's `PipelineStep`.
- `web/components/common/layout_components.py:26-46` — dead `navigation_menu` with stale page names.

---

## What we checked and cleared (calibration)

43 reader findings were **refuted** on inspection — useful negatives that show the boundaries hold:
- `_validateVars` "fabricates 0" — false; `StatType.content` is never `None` (initialized `[]`,
  getter raises otherwise).
- `portfolio_service` "bare except" — it's `except Exception` (not bare `except:`), it logs, and it's
  intentional graceful degradation for an injected presentation callback.
- Manager no-op `return df` paths — no `inplace` mutation; hard rule #3 is about mutation, not object
  identity (though `outlier_service` active paths do return pandas views — a separate latent nit).
- `csv_contract.py` file-I/O in models — stdlib-only, zero coupling/cycle; cohesion smell at most.
- `registry` `SimulatorInfo` frozen-with-mutable-lists — no mutation exists anywhere; latent only.

---

## Recommended fix order

1. **M1, M5** — real bugs (state corruption; failure masked as empty). Cheap, high value.
2. **M2, M3 + Theme A** — restore dual-engine fidelity by moving Plotly specifics behind neutral
   intent models. Highest architectural leverage.
3. **S1, S2, S3** — fix the three dependency-direction violations; add greps to `arch-check` so they
   can't regress (models→services, parsing→services, web→state-manager).
4. **Theme C** — decide the copy-on-read contract and apply it uniformly; freeze `FigureConfig`.
5. **M4, Theme E** — delete duplicated/dead surface; route the view's pipeline run through the facade.
6. **Theme B/D** — consolidate per-plot-type reshape logic; remove sim-specific literals from views.
