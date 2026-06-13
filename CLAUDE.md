# CLAUDE.md — RING-5

> Canonical working guide for Claude Code in this repository. It is the **single source of truth**
> for architecture, commands, conventions, and extension recipes. It was authored from a
> line-by-line analysis of every module (Mar 2026 codebase) and supersedes all prior AI-agent
> docs. If something here disagrees with the code, **the code wins** — fix this file.

**RING-5** = *Reproducible Instrumentation for Numerical Graphics for gem5*. A Streamlit web app
that turns raw simulator stats (`stats.txt`) into publication-ready figures (bar/line/scatter/
histogram/heatmap + grouped/stacked/dual-axis variants), with a no-code transform pipeline and
portable "portfolio" snapshots. Python 3.12+, gem5 today, multi-simulator by design.

---

## 1. Hard rules (non-negotiable — enforced by pre-commit hooks, CI, and `make arch-check`)

1. **Never run git mutations.** Version control is human-only here (`git add/commit/push/branch/
   merge/rebase/reset/...`). Read-only git (`status`, `log`, `diff`) is fine. Do not commit unless
   the user explicitly asks.
2. **No Streamlit in `src/core/`.** No `import streamlit` / `from streamlit` and no
   `st.session_state` anywhere under `src/core/` or `src/parsing/`. UI state lives only in `src/web/`.
3. **No `inplace=True`** on DataFrames anywhere in `src/`. Always return new objects (`.copy()` first).
4. **No bare `except:`** in `src/`. Catch specific exceptions; raise/log, never silently swallow.
5. **No `eval()` / `exec()`** in `src/` production code. No `pickle.load` on untrusted data.
6. **Never fabricate data.** If a gem5 regex fails to match, raise or log — never guess a value.
7. **Async API only** for parse/scan — never add synchronous wrappers (see §6).

Run `make arch-check` after structural changes; all five boundary checks must return empty.

---

## 2. Architecture — 3 layers, strict one-directional dependency

```
Layer C  Presentation   src/web/ + app.py        Streamlit UI, Plotly/Matplotlib rendering
   │ (calls)
Layer B  Domain          src/core/services/, src/core/state/, src/core/common/
   │ (calls)             business logic, pipelines, state — NO UI imports
Layer A  Data            src/parsing/  +  src/core/models/
                         file I/O, gem5 parsing, scanning, immutable data models
```

Dependency rule: **Web → Core ← Parsing.** Core never imports web or streamlit. Core reaches
Parsing only through the facade. `src/core/models/` is the shared "common language" (TypedDicts,
frozen dataclasses, Protocols) imported by everyone, depending on nobody.

~244 Python modules, ~39.6k LOC in `src/`, plus a Perl parsing layer.

### The facade (the one entry point the UI uses)

`src/core/application_api.py` → **`ApplicationAPI`** (constructed once, cached via
`@st.cache_resource` in `app.py`). It:
- exposes service sub-APIs as properties: **`api.managers`**, **`api.data_services`**, **`api.shapers`**
  (composed by `DefaultServicesAPI(state_manager)` in `src/core/services/services_impl.py`);
- owns the `RepositoryStateManager` (single source of truth for session state);
- orchestrates parse/scan via an injected `SimulationParser` (defaults to gem5 via registry);
- delegates previews, history, visualization config, simulator-registry lookups.

> The facade is `ApplicationAPI` (`src/core/application_api.py`). There is **no** `src/web/facade.py`.

### The public package (`ring5/` — headless composition root)

Top-level **`ring5/`** is the supported programmatic surface (`import ring5` + the `ring5` CLI,
registered via `[project.scripts]`). Like `app.py`, it is a **composition root**: it may import
both `src.core` and `src.web` (the layer rules below it are untouched — never "fix" its web
imports). It wires `ApplicationAPI(plot_deserializer=BasePlot.from_dict)` and adds the seams the
facade never had:
- **`ring5.Session`** — parse (`ParseJob` handles carry strategy/var_names; strict missing-stat
  detection), load/shape/managers, `create_plot` (snake_case types), `render(plot, engine=…)`
  (engine is always an explicit per-call argument — never `EngineManager`/session state),
  `export(fig, path, deterministic=…)`, portfolio save (`overwrite=False` default) / load
  (returns `RestoreReport`).
- **`ring5.render_portfolio(name, out_dir, …)`** — the reproducibility flagship: restore a
  snapshot and regenerate every figure file headlessly (CLI: `ring5 render`).
- **`ring5.doctor()`** (perl/chrome/xelatex preflight), **`ring5.shutdown()`** (process pools),
  typed errors under `ring5.Ring5Error`.
- **`ring5.FigureSpec`** (+ `FigureSpecBuilder`, `DualAxisOpts`, `LegendOpts`, `ReferenceLineOpts`
  in `ring5/figure_spec.py`) — an optional typed front-end over the flat config dict so callers
  get autocomplete/validation instead of grepping ~80 keys. Pure dataclasses (no pandas/mpl, so
  eagerly exported); `spec.to_config()` feeds `Session.create_plot(config=…)`. The long tail of
  flat keys stays reachable via `FigureSpec.extra`.
- Rendering executes the exact UI sequences (`create_figure` + `apply_common_layout`; mpl path
  via `ConfigSpecBuilder`→`enrich_from_plotly`→`resolve_config`→connector). Byte-export functions
  live UI-free in `src/web/rendering/figure_export.py` (with `deterministic=True` knobs for CI);
  `download_section.py` is only the Streamlit presentation around them.
- Keystone test: `tests/integration/test_ring5_public_api.py`. User docs:
  `docs/user-guide/features/scripting.md`.

### State (Repository pattern)

`src/core/state/repository_state_manager.py::RepositoryStateManager` (implements the
`StateManager` Protocol in `state_manager.py`) delegates to `SessionRepository` (aggregate root),
which owns 7 repositories in `src/core/state/repositories/`: `data`, `plot`, `parser_state`,
`config`, `history`, `preview`, `visualization`. Pure in-memory, defensive-copy on read.
Portfolio restore uses an injected `PlotDeserializer` so core never imports web.

### Parsing (Layer A, multi-simulator)

- `src/parsing/parser_protocol.py::SimulationParser` — the protocol every backend implements
  (`submit_parse_async`, `finalize_parsing`, `submit_scan_async`, `aggregate_scan_results`).
  Scan cancellation is handle-based and instance-scoped: `ApplicationAPI.cancel_pending_scans()`
  cancels only the futures that instance submitted (pool facades hold no future references).
  NOTE: the web app caches ONE instance process-wide, so there it spans all browser sessions;
  ring5 scripts (one instance per Session) get true per-session scoping.
- `src/parsing/registry.py::SimulatorRegistry` — class-level registry (`SimulatorInfo` metadata +
  lazy factory + cached instance). gem5 auto-registers at import. `get_parser("gem5")`.
- `src/parsing/framework/` — **simulator-agnostic** shared infra every backend builds on:
  `work_pool.py::WorkPool` (one `ThreadPoolExecutor` singleton, `shutdown()`+`atexit`),
  `job.py::Job` (work-unit ABC), `file_discovery.py::find_stats_files`.
- `src/parsing/gem5/` — the only backend today:
  - `impl/gem5_parser.py::Gem5Parser` — **the gem5 backend** (parse + scan + CSV assembly);
    implements `SimulationParser`, and is what the registry instantiates. Methods are static (the
    pools are singletons), so callable on the class or the registry's instance.
  - `impl/pool/pool.py` — `ScanWorkPool`/`ParseWorkPool` facades over the framework `WorkPool`.
  - `impl/strategies/perl_worker_pool.py::PerlWorkerPool` — **persistent Perl processes** (the 54×
    speedup); also `shutdown()` + `atexit`.
  - `impl/strategies/` — `simple` and `config_aware` strategies via `StrategyFactory`.
  - `impl/scanning/pattern_aggregator.py` — collapses `system.cpu0..15.numCycles` →
    `system.cpu\d+.numCycles` (≈94% variable reduction).
  - `types/` — self-registering stat types via `@register_type("name")` on `StatTypeRegistry`:
    `scalar`, `vector`, `distribution`, `histogram`, `configuration`. Lifecycle invariant:
    `balance_content()` → `reduce_duplicates()` **must** run before `reduced_content` is read.
  - `perl/` — `fileParser.pl`, `fileParserServer.pl` (persistent server), `statsScanner.pl`, and
    `libs/` regex modules (`TypesFormatRegex.pm`, `Scanning/Type/*.pm`).

### Shapers (Layer B — the no-code transform pipeline)

Strategy + Factory. `src/core/services/shapers/factory.py::ShaperFactory._registry` maps **camelCase**
keys to classes; impls in `src/core/services/shapers/impl/`:
`mean`, `columnSelector`, `conditionSelector` (=Filter), `itemSelector`, `normalize`,
`pivotLonger`, `pivotWider`, `sort`, `splitApply`, `transformer`. Base: `Shaper(ABC)` (abstract
`_verify_params`, `_verify_preconditions`, `__call__(df)->df`); `UniDfShaper(Shaper)` for
single-frame ops. Configs are a **discriminated union** in `src/core/models/shaper_models.py`
(per-type `TypedDict`, discriminated by `type`). Shapers are stateless, immutable (`.copy()`),
and pipeable; pipeline run + fingerprint caching in `shapers/pipeline_service.py`. UI configs:
`src/web/components/shapers/`.

### Plots & rendering (Layer C)

- `src/web/pages/ui/plotting/plot_factory.py::PlotFactory._plot_classes` maps **snake_case** keys to
  `BasePlot` subclasses in `types/`: `bar`, `line`, `scatter`, `histogram`, `heatmap`, `grouped_bar`,
  `stacked_bar`, `grouped_stacked_bar`, `dual_axis_bar_dot`. (`GroupedStackedBarPlot` extends
  `StackedBarPlot`, not `BasePlot` directly.) `dual_axis_bar_dot` is WIP (excluded from coverage).
- `BasePlot` (`base_plot.py`, `ABC` + `PlotConfigUIMixin`): implement **`create_traces(data, config)
  -> TraceBuildResult`** and **`get_legend_column(config) -> str | None`**. `create_figure()` is
  provided (delegates to traces). Traces are **engine-agnostic** (`TraceConfig` dataclasses).
- Rendering pipeline: `FigureConfig` (`src/core/models/visualization/`) is the single styling source
  of truth → `config_resolver.resolve_config()` replaces **`-1`/`-1.0` sentinels** ("inherit") →
  engine connectors `src/web/rendering/{plotly_connector,matplotlib_connector}.py` apply styles in
  the **exact 16-step `STYLING_PIPELINE_ORDER`** (`src/web/rendering/_connector_protocol.py`):
  backgrounds → font_family → color_palette → title → axis_labels → axis_ticks → axis_ranges →
  axis_colors → grids → legends → reference_lines → data_labels → annotations → separators →
  hatching → margins. Trace conversion: `trace_to_plotly.py` / `matplotlib_trace_renderer.py`.
- `src/web/rendering/engine_manager.py::EngineManager` switches `plotly`/`matplotlib` via the
  `ring5_engine_mode` session key. Default palette is **`wong`** (colorblind-safe).
- **Grouped-bar extras** (computed in `GroupedBarUtils.calculate_grouped_coordinates`, rendered
  by both engines): `category_groups={cat: label}` draws a bolder boundary separator at each label
  change (even when `show_separators=False`; an `isolate_last_group` boundary keeps its line) plus a
  centered super-group label under each contiguous run, and — on by default — a `\cmidrule`-style
  **span rule** above each label. The span rule is an engine-agnostic `RuleLine` (data-x, paper-y)
  in `TraceBuildResult.rule_lines`, drawn by `trace_to_plotly` (paper-yref line) and
  `matplotlib_connector.draw_layout_shapes` (blended transform, `clip_on=False`); it threads through
  `build_matplotlib_figure` / `chart_display` / `render_controller` / `ring5._render`. Per-label
  rotation via `major_label_rotation_overrides={label: deg}`. Palette config also accepts a hex
  **list** (`palette_service.resolve_palette`).
- UI state: `src/web/state/ui_state_manager.py::UIStateManager` — namespaced keys
  `plot.{id}.*`, `manager.*`, `nav.*`, `export.*`. Controllers: `src/web/controllers/plot/`
  (`creation`, `pipeline`, `render`). Pages: `src/web/pages/` (`data_source`, `data_managers`,
  `manage_plots`, `portfolio`, `documentation`); `app.py` is the nav shell.

### End-to-end happy path

Data Source → scan variables → parse → CSV → Manage Data (seeds reduce / outliers / arithmetic /
mix) → Manage Plots → create plot → build shaper pipeline → **finalize** → set X/Y → render/preview
→ export → Portfolio save/load.

---

## 3. Commands (use the Makefile; venv is `python_venv/`)

```bash
make dev                # create venv + install -e ".[dev]"   (then: make pre-commit-install)
make run                # streamlit run app.py   (http://localhost:8501)
                        # headless: ./python_venv/bin/ring5 {doctor,parse,render,upgrade}
make test               # unit + integration, no coverage gate (downloads test data on first run)
make test-unit          # unit only, fast
make test-ci            # full suite + 90% coverage gate (what main-branch CI enforces)
make test-visual        # Playwright UI/visual tests (spins up Streamlit on :8502)
make quality-gate       # arch + mypy + black + flake8 + security, all-in-one
make arch-check         # just the 5 architecture-boundary greps
make pre-commit         # run all pre-commit hooks on all files
make install-latex      # system TeX for PDF/PGF/EPS export (interactive, uses sudo)
```

Direct tools (prefer venv binaries):
```bash
./python_venv/bin/pytest tests/unit/test_X.py -v        # one file
./python_venv/bin/mypy src/ --show-error-codes          # types (config in pyproject.toml)
./python_venv/bin/black src/ tests/                     # format (line-length 100)
./python_venv/bin/flake8 src/ tests/
./python_venv/bin/bandit -r src/ -c pyproject.toml -ll
```

- pytest runs with `-n 3 --dist loadgroup` (xdist). **Keep `-n 3`; never `-n auto`** (stability).
- `tests/data/` is downloaded on demand by `make test-data` (GitHub release tarball).
- CI (`.github/workflows/ci.yml`): quality-checks → tests(+cov, `--timeout=60`) → e2e Playwright
  (only on push to `main`). Perl is required for parsing tests.

---

## 4. Test layout (268 files, ~3.8k test functions — README's "1110" is stale)

| Dir | What | Browser? |
|-----|------|----------|
| `tests/unit/` (162) | pure functions / classes | no |
| `tests/integration/` (36) | cross-component workflows | no |
| `tests/ui/` (10) | Streamlit `AppTest` (the old 1.53.1 ButtonGroup monkey-patch was removed — fixed upstream in 1.58) | no |
| `tests/ui_logic/` (13) | controllers / UI logic | no |
| `tests/ui_unit/` (16) | UI components with mocked `st` | no |
| `tests/e2e/` (11) | Playwright, marker `requires_browser`, Page Object Model | **yes** |
| `tests/visual/` (21) | screenshots/visual (excluded from default collection) | **yes** |
| `tests/performance/` (2) | benchmarks (`benchmark` marker) | no |
| `tests/tests_principle_compliance/` (11) | architecture-guard tests (excluded from default) | no |
| `tests/helpers/` | fixtures; `tests.helpers.gem5_fixtures` is a registered pytest plugin | — |

Root `tests/conftest.py` provides `mock_api`, `sample_data`, `sample_data_extended`,
`sample_pipeline_config`, `mock_state_manager`, `e2e_sample_data`, the `columns_side_effect` helper
for mocking `st.columns`, and an autouse session cleanup of the Perl worker pool. **Reuse
`columns_side_effect` — don't redefine it.** `norecursedirs` skips `tests_principle_compliance`,
`manual`, `data`, `visual`. Markers: `requires_latex`, `requires_browser`, `benchmark`, `smoke`,
`slow`, `xdist_group`, `data_value`. `xfail_strict = true`.

For deeper testing recipes (esp. Streamlit×Playwright gotchas) see
`.claude/skills/e2e-streamlit-testing/`.

---

## 5. Extending the system → use the skills in `.claude/skills/`

| Task | Skill | One-line recipe |
|------|-------|-----------------|
| New plot type | `add-plot-type` | subclass `BasePlot` in `pages/ui/plotting/types/`, impl `create_traces`+`get_legend_column`, register in `PlotFactory` (snake_case), add config UI |
| New shaper | `add-shaper` | subclass `Shaper`/`UniDfShaper` in `core/services/shapers/impl/`, add `*ShaperConfig` TypedDict, register in `ShaperFactory` (camelCase), add UI in `web/components/shapers/` |
| Parsing / new gem5 var type / async debugging | `parsing-and-variable-types` | `@register_type` a `StatType`, add Perl `Type/*.pm` regex, wire `TypesFormatRegex`, test Perl then via `ApplicationAPI` |
| Figure styling / dual-engine | `rendering-figureconfig` | edit `FigureConfig` + apply in **both** connectors in `STYLING_PIPELINE_ORDER`; sentinels resolved before connectors |
| E2E / UI tests | `e2e-streamlit-testing` | POM, `data-testid` selectors, segmented-control toggle & fragment-rerun gotchas |
| New simulator backend | (see §2) | implement `SimulationParser`, `SimulatorRegistry.register(SimulatorInfo, factory)` |

**Verification gates & cleanup** — consult/run before merging. Each is self-maintaining: it edits
its own `SKILL.md` in place (present tense, canon-only) when the code drifts, and writes a memory for
durable facts.

| Gate | Skill | Checks |
|------|-------|--------|
| Architecture | `architecture-check` | the 7 hard rules + the 8 boundary greps (`make arch-check` / `quality-gate`) |
| Facade / API | `api-check` | `ApplicationAPI` contract, the 3 sub-APIs, async parse/scan, no direct core reach-around |
| Web / UI | `ui-check` | Page→Controller→Component (no presenter), namespaced UI state, dual-engine, UI test layers |
| Plot type | `plot-type-check` | `BasePlot` contract, engine-agnostic traces, `PlotFactory` registration, dual-engine render |
| Parser correctness | `parser-check` | no fabrication, async-only, StatType lifecycle, Perl regex duplication, pool lifecycle |
| Parser perf / robustness | `parser-improvement` | speed up / harden parsing behind the correctness invariants |
| Stale paths & docs | `clean-stale-paths` | sweep dead/duplicated/stale paths in code+docs; enforce canon-only docs |

---

## 6. Conventions & gotchas

- **Async parse/scan pattern** (never wrap synchronously):
  ```python
  futures = api.submit_scan_async(stats_path, pattern, limit=5)
  variables = api.finalize_scan([f.result() for f in futures])
  batch = api.submit_parse_async(stats_path, pattern, variables, out_dir, scanned_vars=variables)
  csv_path = api.finalize_parsing(out_dir, [f.result() for f in batch.futures])
  ```
  Always pass `scanned_vars` when parsing regex/pattern variables (needed to resolve concrete names).
- **Naming asymmetry:** shaper registry keys are **camelCase** (`columnSelector`, `pivotLonger`);
  plot registry keys are **snake_case** (`grouped_bar`, `dual_axis_bar_dot`). Don't mix them up.
- **Legend hierarchy:** config prefixes `legend_*` (primary), `legend2_*` (secondary), `legend3_*`
  (tertiary). Semantic by role — never the word "boxed".
- **Error-bar convention:** a std-dev column is the value column name + `.sd` suffix (e.g. `ipc.sd`).
- **Sentinels:** `-1` / `-1.0` in `FigureConfig` mean "inherit"; `config_resolver.resolve_config()`
  removes them before any connector runs — connectors never see `-1`.
- **Settings ownership:** tick marks / tick pad / grid dash → Axes pill (not Typography). Typography =
  font sizes/colors only. Y-axis title standoff & vshift → Axes Y-Left pill. Settings UI uses
  progressive disclosure (basic → advanced) and `render_reorderable_list(enable_rename=True)`.
- **Discriminated unions:** any model with a `type` field uses per-type `TypedDict`s, not one flat
  mega-dict.
- **Matplotlib figures:** `chart_display.py` calls `plt.close()` and caches the figure under
  `plot.{id}.mpl_fig` in session_state (session-scoped render cache — intentional, never serialized
  to disk). `matplotlib_connector.py` correctly does **not** close (Streamlit's `st.pyplot` handles it).
- **Mandatory patterns:** Strategy (parsers/strategies), Factory (plots/shapers/parser), Builder
  (`FigureConfig`), Facade (`ApplicationAPI`), Singleton (pools), Repository (state), Discriminated
  Union (typed configs), Component (self-contained Streamlit widgets — **no presenter layer**).

### Removed features — do NOT re-add
Performance page · "View Current Data" expander · Pipeline save/load dialogs · Workspace management
(download/process/save-all) · Reference-Line-Normalizer shaper · Customization settings pill ·
**the Presenter layer** (replaced by components in refactor v2).

### Known real issues (verified; small — fix if you touch the area, don't trust old "critical bug" lists)
- `src/web/models/plot_models.py`: `PlotConfig = dict[str, Any]` is an **intentional** progressive-typing
  alias (the typed schema is `PlotDisplayConfig`); narrowing it is a gradual site-by-site migration, not
  a bug to "fix".

> **Resolved (Jun 2026, package-upgrade pass):** the dead presenter stub and all Phase-10 shims
> (`models/visualization/resolvers.py`, `services/plot_interaction_service.py`, the `palettes.py`
> re-export) were deleted; `vector.py`/`scalar.py` no longer truncate floats via `int()` on ingestion
> or reduction; `figure_config.py`/`legend_config.py`/`portfolio_migrator.py` `from_dict`/`migrate` no
> longer mutate their caller's input dict; the manager-history docstrings already say 10. Dependency
> floors were bumped to latest (pandas 3.0, numpy 2.4, streamlit 1.58, plotly 6.8, kaleido 1.3, mypy
> 2.1, black 26.5, pytest 9.0.3, …) — quality gate stays green.

> The old `.github/copilot-instructions.md` listed 8 "CRITICAL bugs" — they are **all false or fixed**:
> outlier removal is correct textbook IQR, `SimpleCache`/`CsvPoolService` have locks, `WorkPool`/
> `PerlWorkerPool` have `shutdown()`+`atexit`, there is no matplotlib leak, `Mean` NaN handling is
> consistent, and `core/common/utils.py` functions are all live. Don't act on that list.

---

## 7. gem5 domain quick-reference

- `stats.txt` is hierarchical (`system.cpu.dcache.overall_miss_rate`); simpoint-aware (multiple
  begin/end dump intervals); `config.ini` carries topology (used by the `config_aware` strategy).
- Variable types: `scalar` (single), `vector` (named entries), `distribution` (min/max/bucketed),
  `histogram` (binned), `configuration` (metadata).
- Pattern aggregation collapses per-core/per-unit repeats into one regex variable with entries.
- Internal/meta stats excluded from selection (from `SimulatorRegistry` `GEM5_INFO.internal_stats`):
  `total, mean, gmean, stdev, samples, sample_period, min_val, max_val, min_bucket, max_bucket,
  num_buckets, underflows, overflows`.

---

## 8. MCP servers (`.mcp.json`)

Project-scoped servers recommended for this repo (Claude Code will ask to approve them):
- **context7** — pulls current docs for fast-moving deps (Streamlit 1.58, Plotly 6.x, pandas 3.x,
  scipy). Use when unsure about a current API: search "use context7" then the symbol.
- **playwright** — drives a real browser; ideal for the Streamlit e2e/visual suite and for
  reproducing UI bugs interactively.

Optional (not enabled by default): a `github` server for PR/issue triage (read-only — remember git
is human-only), and a `fetch` server (the built-in WebFetch/WebSearch usually suffice).

---

## 9. Pointers

- Published docs (GitHub Pages, keep authoritative for users): `docs/` →
  `nikiitin.github.io/RING-5`, organized as three trees: `docs/user-guide/`, `docs/developer-guide/`,
  `docs/ai-knowledge-base/`. **Document only the one canonical way to do a thing** — present tense,
  no "was X, now Y" narration (the lone exception is `architecture/history.md`, the single place
  history is allowed to live). If a doc path disagrees with the code, the code wins — fix the doc.
- Dev tooling: `Makefile`, `pyproject.toml` (black/flake8/mypy/pytest/bandit config),
  `.pre-commit-config.yaml` (14 hooks incl. the local architecture hooks), `.trunk/` (trunk.io),
  `.streamlit/config.toml` (theme), `CONTRIBUTING.md` (note: its test/coverage numbers are stale).
- Skills: `.claude/skills/`. Memory: `~/.claude/.../memory/`.
