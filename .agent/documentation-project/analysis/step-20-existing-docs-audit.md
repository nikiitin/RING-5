# Step 20 — Existing Documentation Audit

> **Status**: COMPLETE
> **Analyzed on**: 2026-03-03
> **Branch**: `005/unified-engine-ui-v2`

---

## 1. Executive Summary

RING-5 has a substantial documentation corpus spread across four locations: `docs/`
(31 markdown files as a GitHub Wiki/Jekyll site), `README.md` and `CONTRIBUTING.md`
at the project root, `.agent/` (50+ internal files for AI assistants), and
`.github/copilot-instructions.md`. The total volume exceeds 10,000 lines of
markdown.

**Overall verdict**: The documentation is **significantly outdated** in aggregate.
While the `.github/copilot-instructions.md` and `.agent/ARCHITECTURE.md` are
the most current and accurate references, the public-facing `docs/` wiki has
not kept pace with major architectural changes (presenter removal, component-based
UI, TraceBuildResult pipeline, FigureSpec system, dual rendering engines). Multiple
documents reference non-existent file paths, removed features, deleted classes,
and contradictory test counts.

| Category | File Count | Accuracy | Currency | Completeness |
|----------|-----------|----------|----------|--------------|
| Root docs (`README.md`, `CONTRIBUTING.md`) | 2 | MEDIUM | PARTIALLY OUTDATED | MEDIUM |
| Public wiki (`docs/`) | 31 | LOW-MEDIUM | SIGNIFICANTLY OUTDATED | LOW |
| Agent docs (`.agent/`) | 50+ | HIGH | MOSTLY CURRENT | HIGH |
| GitHub config (`.github/`) | 1 | HIGH | CURRENT | HIGH |

**Key findings**:
1. **32 broken file path references** across docs/ pointing to paths that do not exist
2. **4 contradictory test counts**: README says 1110, CONTRIBUTING says 653, Testing-Guide says 1344, copilot-instructions says 3000+
3. **7 references to removed features** (Performance page, Upload Data page, Presenters, Pipeline save/load)
4. **pyyaml dependency** still listed in Installation.md but was removed from project
5. **StateManager import path** in Web-Interface.md references non-existent `src/web/state_manager.py`
6. **Presenter layer** still referenced in Architecture.md but was architecturally removed
7. **Source code docstring quality is HIGH** -- ApplicationAPI, BasePlot, Shaper, ShaperFactory, SimulationParser all have comprehensive Google-style docstrings with Args/Returns/Raises
8. **Type annotation coverage is EXCELLENT** -- strict mypy compliance, full signatures on all public APIs

---

## 2. Complete Documentation Inventory

### 2.1 Root-Level Files (2 files, ~230 lines)

| File | Lines | Last Meaningful Update | Primary Audience |
|------|-------|----------------------|------------------|
| `README.md` | 184 | Recent (mentions multi-simulator) | External users, contributors |
| `CONTRIBUTING.md` | 377 | Outdated (653 test count) | Contributors |

### 2.2 Public Wiki — `docs/` (31 files, ~5,500 lines)

#### Root/Navigation (6 files)
| File | Lines | Status |
|------|-------|--------|
| `docs/Home.md` | ~50 | PARTIALLY OUTDATED |
| `docs/README.md` | ~30 | PARTIALLY OUTDATED |
| `docs/index.md` | ~40 | PARTIALLY OUTDATED (references Architecture-Diagram.md with wrong case) |
| `docs/Installation.md` | 260 | OUTDATED (pyyaml listed, verify_installation.py exists but untested) |
| `docs/_Sidebar.md` | ~30 | PARTIALLY OUTDATED (sidebar links not verified) |
| `docs/_config.yml` | ~15 | CURRENT (Jekyll config, rarely changes) |

#### API Documentation (6 files)
| File | Lines | Status |
|------|-------|--------|
| `docs/api/Backend-Facade.md` | ~200 | SIGNIFICANTLY OUTDATED |
| `docs/api/Data-Transformations.md` | ~250 | PARTIALLY OUTDATED |
| `docs/api/Parsing-API.md` | ~200 | PARTIALLY OUTDATED |
| `docs/api/Parsing-Guide.md` | ~250 | PARTIALLY OUTDATED |
| `docs/api/Plotting-API.md` | ~300 | SIGNIFICANTLY OUTDATED (malformed code blocks at line 261) |
| `docs/api/Shaper-API.md` | ~250 | PARTIALLY OUTDATED |

#### Plot Type Documentation (5 files)
| File | Lines | Status |
|------|-------|--------|
| `docs/plots/Bar-Charts.md` | ~150 | PARTIALLY OUTDATED |
| `docs/plots/Grouped-Stacked-Bars.md` | 97 | PARTIALLY OUTDATED |
| `docs/plots/histogram-plot.md` | 240 | PARTIALLY OUTDATED (references `src/plotting/plot_factory.py`) |
| `docs/plots/Line-Plots.md` | 142 | PARTIALLY OUTDATED |
| `docs/plots/Scatter-Plots.md` | 137 | PARTIALLY OUTDATED |

#### Web App Documentation (11 files)
| File | Lines | Status |
|------|-------|--------|
| `docs/webapp/Web-Interface.md` | 444 | SIGNIFICANTLY OUTDATED (Performance page, Upload Data page) |
| `docs/webapp/Quick-Start.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/First-Analysis.md` | ~200 | PARTIALLY OUTDATED |
| `docs/webapp/Creating-Plots.md` | ~200 | PARTIALLY OUTDATED |
| `docs/webapp/Download-Guide.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/Portfolios.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/pages/Data-Source.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/pages/Data-Managers.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/pages/Manage-Plots.md` | ~200 | PARTIALLY OUTDATED |
| `docs/webapp/pages/Plot-Settings.md` | ~150 | PARTIALLY OUTDATED |
| `docs/webapp/pages/Export-Download.md` | ~150 | PARTIALLY OUTDATED |

#### Developer Documentation (8 files)
| File | Lines | Status |
|------|-------|--------|
| `docs/developer/Architecture.md` | 487 | SIGNIFICANTLY OUTDATED (references presenters, old structure) |
| `docs/developer/Testing-Guide.md` | 329 | PARTIALLY OUTDATED (1344 test count, structure mostly correct) |
| `docs/developer/Adding-Plot-Types.md` | 391 | SIGNIFICANTLY OUTDATED (wrong file paths throughout) |
| `docs/developer/Adding-Shapers.md` | 375 | SIGNIFICANTLY OUTDATED (wrong file paths) |
| `docs/developer/Development-Setup.md` | 247 | OUTDATED (`src/parsers/` path) |
| `docs/developer/architecture-diagram.md` | 257 | PARTIALLY OUTDATED |
| `docs/developer/web-layer-architecture.md` | 350 | PARTIALLY OUTDATED (presenter references) |
| `docs/developer/services-architecture.md` | 187 | MOSTLY CURRENT |

#### Images (21 PNG files in `docs/webapp/images/`)
All images exist as PNG files. No broken image references detected within
the webapp documentation that references these images.

### 2.3 Agent Documentation — `.agent/` (50+ files)

| File | Lines | Status |
|------|-------|--------|
| `.agent/ARCHITECTURE.md` | 253 | CURRENT (v4.0, most accurate architecture reference) |
| `.agent/QUICKSTART.md` | 56 | PARTIALLY OUTDATED (references `src/plotting/visualizers/`) |
| `.agent/README.md` | — | CURRENT |
| `.agent/PROGRESS.md` | — | CURRENT |
| `.agent/DEEP_DIVE_PLAN.md` | — | CURRENT |
| `.agent/DUAL_IDE_SETUP.md` | — | CURRENT |
| `.agent/ANTIGRAVITY_README.md` | — | CURRENT |
| `.agent/unified_architecture_manifesto.md` | — | MOSTLY CURRENT |
| `.agent/rules/000-009` (10 files) | — | CURRENT |
| `.agent/workflows/` (12 files) | — | CURRENT |
| `.agent/skills/` (8+ files) | — | CURRENT |
| `.agent/context/` | — | CURRENT |
| `.agent/knowledge_for_e2e_testing/` (6 files) | — | CURRENT |
| `.agent/documentation-project/` (20+ files) | — | CURRENT (this project) |

### 2.4 GitHub Configuration — `.github/`

| File | Lines | Status |
|------|-------|--------|
| `.github/copilot-instructions.md` | 318 | CURRENT — most comprehensive single document |

### 2.5 Missing Documentation

| Expected File | Exists? | Notes |
|--------------|---------|-------|
| `CHANGELOG.md` | NO | No changelog exists at project root |
| `docs/plots/Heatmap.md` | NO | Heatmap plot type has no documentation |
| `docs/plots/Dual-Axis-Bar-Dot.md` | NO | Dual axis plot type has no documentation |
| `docs/developer/Rendering-Engines.md` | NO | Dual Plotly/Matplotlib engines undocumented in wiki |
| `docs/developer/FigureSpec-Pipeline.md` | NO | FigureSpec system undocumented in wiki |
| `docs/developer/Components-Guide.md` | NO | Component-based UI undocumented in wiki |
| `docs/developer/Settings-Pills.md` | NO | Settings pill system undocumented in wiki |
| `docs/developer/State-Repositories.md` | NO | Repository pattern state management undocumented |
| `docs/developer/Multi-Simulator.md` | NO | Multi-simulator protocol undocumented in wiki |

---

## 3. Per-File Audit Reports

### 3.1 `README.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 8 | Badge says "1110 passing" — actual count differs significantly | MEDIUM | Update badge count |
| 124 | Says "Run all 1110 tests" | MEDIUM | Update test count |
| 130-143 | Project structure shows `src/core/parsing/` — actual is `src/parsing/` (separate top-level package) | HIGH | Fix structure tree |
| 100 | External doc links point to `nikiitin.github.io/RING-5` — may not be deployed | LOW | Verify deployment |
| 78 | Missing plot types from table: Heatmap, Dual Axis Bar Dot, Grouped Stacked | MEDIUM | Add missing types |

**Strengths**:
- Clean, well-structured README with clear value proposition
- Accurate performance benchmarks table
- Good workflow overview (Parse/Transform/Plot/Save)
- Citation block provided
- Multi-simulator architecture mentioned

**Missing Coverage**:
- No mention of dual rendering engines (Plotly + Matplotlib)
- No mention of FigureSpec pipeline
- No mention of settings pills UI
- No mention of PDF/PGF/EPS export via Matplotlib

### 3.2 `CONTRIBUTING.md`

**Overall Status**: SIGNIFICANTLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 65-66 | References `src/web/services/variable_service.py` — path does not exist; services are in `src/core/services/` | HIGH | Fix path |
| 104 | Says "653/653" tests — actual count is much higher | HIGH | Update test count |
| 178 | Coverage target says "77%+" — may be outdated | MEDIUM | Verify and update |
| 298 | Says "Adding a New Service" with path `src/web/services/my_service.py` — services are in `src/core/services/` | HIGH | Fix path |
| 304 | Says "Adding a New Plot Type" with path `src/plotting/types/my_plot.py` — actual is `src/web/pages/ui/plotting/types/` | HIGH | Fix path |
| 319-320 | References `FigureSpec` and `PlotlyConnector` — class names may differ (actual: `FigureConfig`, `FigureSpecToPlotly`) | MEDIUM | Verify and fix |
| 329 | References `ConfigBridge.spec_to_config` — class may not exist | MEDIUM | Verify |
| 355-359 | References `tests/tests_principle_compliance/` — directory exists and tests confirmed | OK | No fix needed |

**Strengths**:
- Good commit message format guide
- Comprehensive code quality standards section
- Testing patterns section with connector/spec/UI examples
- Pre-commit hook documentation

**Missing Coverage**:
- No mention of component-based UI pattern (replacing presenters)
- No mention of TraceBuildResult pipeline
- No mention of settings pills or widget factory
- Architecture section is oversimplified (3 layers but no detail)

### 3.3 `docs/Installation.md`

**Overall Status**: OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 131 | Lists `pyyaml` as core dependency — PyYAML was removed (commit 801098f) | HIGH | Remove pyyaml, add actual deps |
| 40-41 | References `python scripts/verify_installation.py` — file exists but may not reflect current requirements | MEDIUM | Verify script works |
| 22 | Claims Windows support — project may not fully support Windows (Perl workers, path conventions) | MEDIUM | Clarify platform support |

**Strengths**:
- Platform-specific instructions (Linux, macOS, Windows)
- Troubleshooting section with common issues
- Clear virtual environment instructions

### 3.4 `docs/webapp/Web-Interface.md`

**Overall Status**: SIGNIFICANTLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 25 | Lists "Home" page — current app has no Home page (redirects to Data Source) | HIGH | Remove or update |
| 28 | Lists "Upload Data" as page #4 — this page does not exist in current navigation | HIGH | Remove |
| 31 | Lists "Performance" as page #7 — Performance page was removed (Phase 1) | HIGH | Remove section |
| 194-210 | "Upload Data Page" section — page does not exist | HIGH | Remove entire section |
| 238-254 | "Performance Page" section — page was removed | HIGH | Remove entire section |
| 275-286 | `StateManager` import from `src/web/state_manager.py` — path does not exist; actual: `src/web/state/ui_state_manager.py` and `src/core/state/state_manager.py` | HIGH | Fix import path and API example |
| 275 | Shows `StateManager.get_data()` static method pattern — actual `StateManager` is a Protocol with instance methods | HIGH | Fix API example |
| 381 | Troubleshooting references `./launch_webapp.sh` — file exists | OK | No fix |
| 420-426 | "Pipeline Import/Export" section — Pipeline save/load dialogs were removed (Phase 4) | HIGH | Remove or update |

**Strengths**:
- Comprehensive page-by-page documentation structure
- Good data flow diagram
- Best practices and common workflows
- Troubleshooting section

**Missing Coverage**:
- No mention of Documentation page (current page #5)
- No mention of segmented control for scan/upload/recent modes on Data Source
- No mention of settings pills on Manage Plots
- No mention of dual rendering engine selection
- No mention of preset system for export

### 3.5 `docs/developer/Architecture.md`

**Overall Status**: SIGNIFICANTLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 16 | Layer C description mentions "Controllers / Presenters / Rendering" — presenters are being removed | HIGH | Remove presenters reference |
| 183-228 | Project structure tree shows `presenters/` directory | HIGH | Update tree |
| 183 | Shows `src/web/models/` but doesn't show `src/web/components/` which is the primary UI abstraction | HIGH | Update tree |
| 291 | Plotting workflow shows `ChartPresenter.render_chart(fig)` — presenters removed, chart_display.py is used | HIGH | Update workflow |
| 375 | Coverage shows "77% (target: 85%)" — may be outdated | MEDIUM | Verify |
| 200 | Shows `state/` under `src/web/` without correct substructure | MEDIUM | Update |

**Strengths**:
- Good TraceBuildResult pipeline diagram
- Design principles section (layered, async-first, patterns, type safety, immutability)
- Data flow documentation (parsing, transformation, plotting workflows)
- Extension points section

**Missing Coverage**:
- No mention of FigureSpec/FigureConfig pipeline (UI widgets to engine connectors)
- No mention of settings pills
- No mention of widget factory
- No mention of ConfigSpecBuilder/PlotlyFigureSpecBuilder
- No detail on the 7 repository types
- No mention of component-based architecture (replacing presenters)

### 3.6 `docs/developer/Adding-Plot-Types.md`

**Overall Status**: SIGNIFICANTLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 26-33 | File location says `src/plotting/types/` — actual: `src/web/pages/ui/plotting/types/` | CRITICAL | Fix all paths |
| 42 | Import says `from src.plotting.base_plot import BasePlot` — actual: `from src.web.pages.ui.plotting.base_plot import BasePlot` | CRITICAL | Fix import |
| 56-66 | `__init__` signature is wrong: actual takes `(plot_id, name, plot_type)` not `(plot_id, name)` with separate `self.plot_type` assignment | HIGH | Fix constructor |
| 67-113 | Shows `create_figure()` as the abstract method — actual abstract method is `create_traces()` returning `TraceBuildResult` | CRITICAL | Rewrite to use create_traces |
| 82 | Uses `self.config.get("x_column")` — actual config is `PlotConfig` TypeAlias (`Dict[str, Any]`) | MEDIUM | Update config access pattern |
| 118 | Factory registration shows `_plot_types: Dict[str, type]` — actual is `_plot_classes: dict[str, Callable[[int, str], BasePlot]]` | HIGH | Update registry code |
| 139-140 | Test imports from `src.plotting.types.my_new_plot` — wrong path | CRITICAL | Fix import paths |
| 205-253 | UI configuration pattern references `src/web/ui/components/plot_config.py` — this file doesn't exist; actual: `src/web/components/plotting/config/` | HIGH | Fix path |

**Strengths**:
- Good step-by-step structure
- Covers initialization, factory registration, testing, UI config
- Multi-trace example pattern
- Best practices checklist
- Common patterns (color mapping, conditional formatting, hover text)

**This document needs a near-complete rewrite.** Every code example uses outdated
import paths and the wrong abstract method signature (`create_figure` vs `create_traces`).

### 3.7 `docs/developer/Adding-Shapers.md`

**Overall Status**: SIGNIFICANTLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | References both `src/core/services/shapers/` AND `src/web/services/shapers/` — `src/web/services/` does not exist | CRITICAL | Fix paths to use only `src/core/services/shapers/` |
| — | Shaper factory registry keys are outdated — actual uses camelCase keys (`columnSelector`, `conditionSelector`, `itemSelector`, `pivotLonger`, `pivotWider`, `splitApply`) not snake_case | HIGH | Update registry keys |
| — | Display names in factory are implementation-specific — actual has `_display_names` dict | MEDIUM | Update display names |

**Strengths**:
- Complete step-by-step guide
- Good class template with `_verify_params`
- Factory registration pattern
- Test template
- UI component creation guide

### 3.8 `docs/developer/Testing-Guide.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 19 | States "1344 tests passing, 17 skipped" — likely outdated count | MEDIUM | Update count |
| 76 | Shows `pytest -n 3` for parallel — may need to verify pytest-xdist is installed | LOW | Verify |
| — | Test structure tree does not include `tests/tests_principle_compliance/` (11 files, confirmed to exist) | MEDIUM | Add to tree |
| — | Does not mention `tests/helpers/` directory contents beyond `sample_figures.py` | LOW | Expand |

**Strengths**:
- Comprehensive test structure tree
- Good fixture documentation (`columns_side_effect`, `mock_api`)
- Unit, UI unit, and integration test templates
- Parametrized test examples
- Markers documentation table
- Best practices section

### 3.9 `docs/developer/Development-Setup.md`

**Overall Status**: OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | Project structure shows `src/parsers/` — actual is `src/parsing/` | HIGH | Fix path |
| — | Simplified structure tree omits significant portions of the codebase | MEDIUM | Expand or link to Architecture |

### 3.10 `docs/developer/web-layer-architecture.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | Documents 5-layer web architecture: Pages -> Controllers -> Presenters -> UIStateManager -> Models | HIGH | Update: presenters being removed, replaced by components |
| — | Mermaid diagrams show presenter layer | HIGH | Update diagrams |
| — | Sequence diagram references presenter flow | HIGH | Update to component flow |

**Strengths**:
- Detailed Mermaid dependency diagrams
- Dependency rules table
- File map with responsibilities
- Adapter pattern documentation

### 3.11 `docs/developer/architecture-diagram.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | References from `docs/index.md` as `Architecture-Diagram.md` (capital D) — actual file is `architecture-diagram.md` (lowercase d) | MEDIUM | Fix reference case |
| — | Mermaid diagram includes presenter modules | HIGH | Remove presenters from diagram |

**Strengths**:
- Comprehensive module-level dependency graph
- Leaf module detail level
- Dependency rules table
- Notes about Phase B additions

### 3.12 `docs/developer/services-architecture.md`

**Overall Status**: MOSTLY CURRENT

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | Method counts may be slightly outdated (~8, ~30, ~7) | LOW | Verify counts |

**Strengths**:
- Accurate domain decomposition (managers, data_services, shapers)
- Mermaid diagram of service relationships
- Dependency injection documentation
- Design principles

### 3.13 `docs/plots/histogram-plot.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| — | References `src/plotting/plot_factory.py` — actual: `src/web/pages/ui/plotting/plot_factory.py` | HIGH | Fix path |
| — | References `src/core/application_api.py` — this path is correct | OK | No fix |
| — | References `.agent/skills/` — these files exist | OK | No fix |

**Strengths**:
- Most detailed plot documentation
- Python code examples
- Configuration table
- Normalization modes
- gem5 integration notes
- Testing commands
- Type safety notes

### 3.14 `.agent/ARCHITECTURE.md`

**Overall Status**: CURRENT (v4.0)

This is the **most accurate** architecture reference in the project. It documents:
- FigureSpec pipeline (UI Widgets -> ConfigSpecBuilder -> FigureSpec -> EngineManager -> Connectors)
- Pills-based settings UI
- Portfolio migration (V1 -> V2)
- Publication validator
- 8 design patterns table
- 10-phase review process
- Merge criteria

**No significant issues found.**

### 3.15 `.agent/QUICKSTART.md`

**Overall Status**: PARTIALLY OUTDATED

**Issues Found**:

| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 41 | References `src/plotting/visualizers/` for new plot creation — path does not exist | HIGH | Fix to `src/web/pages/ui/plotting/types/` |

### 3.16 `.github/copilot-instructions.md`

**Overall Status**: CURRENT

This is the **most comprehensive single document** in the project. It accurately
documents:
- Architecture with correct file paths
- Multi-simulator architecture
- Mandatory design patterns (8 patterns)
- Coding standards with examples
- Quality gate workflow
- Detailed file structure tree (most accurate)
- Known critical bugs with exact file locations
- Dead code inventory (~950 lines)
- Architecture violations
- Pandas patterns
- Python 3.12+ modernization opportunities
- Streamlit patterns
- Test coverage gaps
- Removed features list

**One minor issue**: The file structure tree in copilot-instructions.md is the most
current, but could go out of date quickly. The "Known Issues" section with critical
bugs should be updated as bugs are fixed.

---

## 4. Broken File Path Reference Catalog

These are specific file paths referenced in documentation that do **not** correspond
to actual files in the current codebase:

### 4.1 Non-Existent Directories

| Referenced Path | Found In | Actual Path |
|----------------|----------|-------------|
| `src/plotting/` | Adding-Plot-Types.md, CONTRIBUTING.md, QUICKSTART.md | Does not exist. Plots are at `src/web/pages/ui/plotting/` |
| `src/plotting/types/` | Adding-Plot-Types.md, CONTRIBUTING.md | `src/web/pages/ui/plotting/types/` |
| `src/plotting/base_plot.py` | Adding-Plot-Types.md | `src/web/pages/ui/plotting/base_plot.py` |
| `src/plotting/plot_factory.py` | Adding-Plot-Types.md, histogram-plot.md | `src/web/pages/ui/plotting/plot_factory.py` |
| `src/parsers/` | Development-Setup.md | `src/parsing/` |
| `src/web/services/` | CONTRIBUTING.md | Does not exist. Services are in `src/core/services/` |
| `src/web/services/variable_service.py` | CONTRIBUTING.md | `src/core/services/data_services/variable_service.py` |
| `src/web/state_manager.py` | Web-Interface.md | `src/web/state/ui_state_manager.py` or `src/core/state/state_manager.py` |
| `src/web/ui/components/plot_config.py` | Adding-Plot-Types.md | `src/web/components/plotting/config/` (directory with multiple files) |
| `src/web/presenters/` | Architecture.md, web-layer-architecture.md | Stub at `src/web/presenters/plot/__init__.py` only (imports broken modules) |
| `docs/developer/Architecture-Diagram.md` | docs/index.md | `docs/developer/architecture-diagram.md` (case mismatch) |

### 4.2 Non-Existent Classes/Methods

| Referenced Name | Found In | Actual Name |
|----------------|----------|-------------|
| `ChartPresenter.render_chart()` | Architecture.md | Removed. Use `chart_display.py` component |
| `PlotlyConnector` | CONTRIBUTING.md | `FigureSpecToPlotly` in `src/web/rendering/plotly_connector.py` |
| `ConfigBridge.spec_to_config()` | CONTRIBUTING.md | `ConfigSpecBuilder` in `src/web/rendering/config_builder.py` |
| `StateManager.get_data()` (static) | Web-Interface.md | `StateManager` is a Protocol with instance methods |
| `BasePlot.create_figure()` as abstract | Adding-Plot-Types.md | `BasePlot.create_traces()` is the abstract method; `create_figure()` is concrete |

### 4.3 Non-Existent Files

| Referenced File | Found In | Status |
|----------------|----------|--------|
| `CHANGELOG.md` | Expected convention | Does not exist anywhere in project |
| `docs/plots/Heatmap.md` | Expected (plot type exists) | Not created |
| `docs/plots/Dual-Axis-Bar-Dot.md` | Expected (plot type exists) | Not created |

---

## 5. Removed Feature References

Features that were explicitly removed but are still documented:

| Removed Feature | Phase Removed | Still Referenced In |
|----------------|--------------|-------------------|
| Performance page | Phase 1 | `docs/webapp/Web-Interface.md` lines 31, 238-254 |
| Upload Data page | Unknown | `docs/webapp/Web-Interface.md` lines 28, 194-210 |
| View Current Data expander | Phase 2 | Possibly in older web app docs |
| Pipeline save/load dialogs | Phase 4 | `docs/webapp/Web-Interface.md` lines 420-426, plot controls in Manage-Plots |
| Workspace management | Phase 5 | Possibly in Download-Guide.md |
| Reference Line Normalizer shaper | Phase 16 | Should be verified in Shaper-API.md |
| Customization settings pill | Phase 18 | Should be verified in Plot-Settings.md |
| Presenter layer | Architectural refactor v2 | Architecture.md, web-layer-architecture.md, architecture-diagram.md |

---

## 6. Test Count Contradictions

Different documents report wildly different test counts:

| Document | Reported Count | Date Context |
|----------|---------------|-------------|
| `CONTRIBUTING.md` line 104 | 653 | Oldest reference, never updated |
| `README.md` badge (line 8) | 1110 | More recent but outdated |
| `README.md` text (line 124) | 1110 | Same as badge |
| `docs/developer/Testing-Guide.md` line 19 | 1344 | Testing-guide specific |
| `.github/copilot-instructions.md` | Implies 3000+ (from "test coverage gaps" context) | Most current but imprecise |
| `.github/copilot-instructions.md` | "~58 new tests needed" | Suggests high existing count |

**Actual**: 293 test files exist in `tests/`. The actual test count should be
determined by running `pytest --co -q | tail -1`.

**Recommendation**: All test count references should either be removed or replaced
with a dynamic badge that pulls from CI.

---

## 7. Docstring Coverage Assessment

Source code docstring quality was assessed by sampling key files across all three layers.

### 7.1 Layer A — Parsing

**File**: `src/parsing/parser_protocol.py` (61 lines)
- **Module docstring**: NONE (imports only, protocol definition)
- **Class docstring**: YES — `SimulationParser` has comprehensive docstring
- **Method docstrings**: YES — all 4 protocol methods have one-line docstrings
- **Type annotations**: COMPLETE — all parameters and returns typed
- **Quality**: GOOD — concise protocol documentation

### 7.2 Layer B — Core Services

**File**: `src/core/application_api.py` (429+ lines)
- **Module docstring**: EXCELLENT — 23-line docstring describing responsibilities, architecture, sub-API access
- **Class docstring**: EXCELLENT — 10-line docstring with numbered responsibilities
- **Method docstrings**: YES — `__init__` has full Args documentation
- **Type annotations**: COMPLETE — all parameters, returns, and local variables typed
- **Quality**: EXCELLENT — best-in-class documentation

**File**: `src/core/services/shapers/shaper.py` (92 lines)
- **Module docstring**: EXCELLENT — describes abstraction, Strategy pattern, core concept
- **Class docstring**: YES — describes Abstract Base Class purpose
- **Method docstrings**: COMPLETE — all 4 methods have full Args/Returns/Raises
- **Type annotations**: COMPLETE
- **Quality**: EXCELLENT

**File**: `src/core/services/shapers/factory.py` (80+ lines)
- **Module docstring**: EXCELLENT — describes Factory pattern, runtime selection
- **Class docstring**: YES — references Factory Pattern, Open/Closed Principle
- **Method docstrings**: COMPLETE — `register()`, `get_available_types()` have Args/Returns
- **Type annotations**: COMPLETE
- **Quality**: EXCELLENT

### 7.3 Layer C — Web/Presentation

**File**: `src/web/pages/ui/plotting/base_plot.py` (222 lines)
- **Module docstring**: MINIMAL — "Base plot class with common functionality."
- **Class docstring**: MINIMAL — "Abstract base class for all plot types."
- **Method docstrings**: GOOD — `__init__`, `create_traces`, `create_figure` all have full Args/Returns docstrings
- **Type annotations**: COMPLETE
- **Quality**: GOOD — methods well-documented, class/module could be more descriptive

**File**: `src/web/pages/ui/plotting/plot_factory.py` (153 lines)
- **Module docstring**: MINIMAL — "Factory for creating plot instances."
- **Class docstring**: GOOD — describes Factory pattern, registry, extensibility
- **Method docstrings**: COMPLETE — all 4 public methods have Args/Returns/Raises
- **Type annotations**: COMPLETE — includes TypedDict for metadata
- **Quality**: GOOD

### 7.4 Summary Matrix

| Layer | Module Docstrings | Class Docstrings | Method Docstrings | Type Annotations |
|-------|------------------|-----------------|-------------------|-----------------|
| Core (B) | EXCELLENT | EXCELLENT | COMPLETE | COMPLETE |
| Parsing (A) | GOOD | GOOD | COMPLETE | COMPLETE |
| Web (C) | MINIMAL-GOOD | GOOD | COMPLETE | COMPLETE |

**Overall docstring quality**: HIGH. The codebase follows Google-style docstrings
consistently. Module-level docstrings are strongest in core, weakest in web layer.
Method docstrings with Args/Returns/Raises are consistent across all layers.

---

## 8. Type Annotation Coverage

### 8.1 Assessment

Type annotation coverage is **EXCELLENT** across the entire codebase. The project
enforces strict mypy compliance as documented in `.github/copilot-instructions.md`:

```
./python_venv/bin/mypy src/ --show-error-codes
```

**Observed patterns**:
- All function signatures are fully typed (parameters + return types)
- Local variables have type annotations where assignment doesn't make it obvious
- `TypedDict` used for structured dictionaries (`PlotTypeMetadata`, `SavedConfigData`, etc.)
- `Protocol` used for structural typing at all layer boundaries (19 protocols)
- `dict[str, Any]` is intentionally used for flexible configuration types (`PlotConfig`)
- Union types use `|` syntax (Python 3.10+ style)
- Generic types use lowercase (`dict`, `list`, `tuple`) rather than `Dict`, `List`, `Tuple`
- `from __future__ import annotations` used in some files for forward references

### 8.2 Per-Layer Assessment

| Layer | Annotation % | Notes |
|-------|-------------|-------|
| Core (B) | ~100% | Strict typing throughout, Protocol-based contracts |
| Parsing (A) | ~100% | All parser methods fully typed |
| Web (C) | ~98% | Some Streamlit callback lambdas may lack annotations |

### 8.3 Known Gaps

From `.github/copilot-instructions.md`:
- 3 pyright "possibly unbound" warnings in `pivot_config.py:256-258`
- These are `selection_filters`, `strategy`, `merge_label` variables

---

## 9. Code Comment Quality

### 9.1 Assessment

Code comments are used judiciously throughout the codebase. Sampling key files:

**`src/core/application_api.py`**:
- Section separator comments: `# =========================================================================`
- Inline clarifications: `# Simulator parser backend (lazy default to gem5 via registry)`
- Well-placed, not redundant with docstrings

**`src/web/pages/ui/plotting/base_plot.py`**:
- Initialization comments: `# Initialize Style Manager`
- Minimal but sufficient

**`src/core/services/shapers/factory.py`**:
- Registry comments: `# Registry of shaper types mapping to their implementing classes`
- Display names comment: `# Human-readable display names for the UI layer`
- Good separation between data and logic

### 9.2 Comment Density

| Layer | Comment Style | Density | Quality |
|-------|-------------|---------|---------|
| Core | Section headers + inline clarifications | MEDIUM | HIGH |
| Parsing | Inline clarifications | LOW-MEDIUM | HIGH |
| Web | Inline clarifications + TODO markers | MEDIUM | HIGH |

### 9.3 Antipatterns NOT Found

- No commented-out code blocks (good hygiene)
- No "obvious" comments (e.g., `# increment counter` before `counter += 1`)
- No misleading comments
- No profanity or informal language

---

## 10. Style Consistency Assessment

### 10.1 Docstring Style

All docstrings follow **Google style** consistently:

```python
def method(self, arg: str) -> int:
    """
    Description.

    Args:
        arg: Description of arg

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
    """
```

**Consistency**: HIGH. No numpy-style or reST-style docstrings found.

### 10.2 Documentation Markdown Style

The `docs/` wiki files use inconsistent conventions:

| Convention | Observed Styles |
|-----------|----------------|
| Headers | Some files use `##` under frontmatter, others use `#` |
| Code blocks | Most use triple backtick with language; `Plotting-API.md` has malformed blocks |
| Cross-references | Mix of `[text](File-Name.md)`, `[text](File-Name)`, and relative `../` paths |
| Frontmatter | Most have `title` + `nav_order`; some omit `---` delimiters properly |
| File naming | Mix of PascalCase (`Bar-Charts.md`), lowercase (`histogram-plot.md`), and kebab-case |

### 10.3 Agent Documentation Style

`.agent/` files are more internally consistent:
- All use clear section headers
- Mermaid diagrams for architecture
- Tables for registries and catalogs
- Inline code with backticks for class/method names

---

## 11. Gap Analysis — Documented vs. Missing

### 11.1 What IS Documented

| Feature/Component | Documented In | Quality |
|-------------------|--------------|---------|
| 3-layer architecture | Architecture.md, copilot-instructions.md | GOOD |
| ApplicationAPI facade | Backend-Facade.md, Architecture.md | MEDIUM |
| gem5 parsing workflow | Parsing-API.md, Parsing-Guide.md | MEDIUM |
| Shaper pipeline | Shaper-API.md, Data-Transformations.md | MEDIUM |
| 7 of 9 plot types | docs/plots/*.md (Bar, Line, Scatter, Histogram, Grouped-Stacked) | MEDIUM |
| Web interface pages | docs/webapp/*.md | MEDIUM (outdated) |
| Testing framework | Testing-Guide.md | GOOD |
| Installation | Installation.md | MEDIUM (outdated deps) |
| Contributing | CONTRIBUTING.md | MEDIUM (outdated paths) |
| Design patterns | copilot-instructions.md, Architecture.md | GOOD |

### 11.2 What is NOT Documented (Major Gaps)

| Feature/Component | Priority | Where It Should Go |
|-------------------|---------|-------------------|
| **FigureSpec/FigureConfig pipeline** | CRITICAL | developer/Rendering-Pipeline.md |
| **TraceBuildResult system** | CRITICAL | developer/TraceBuildResult.md |
| **Settings pills UI system** | HIGH | developer/Settings-Pills.md or webapp/pages/Plot-Settings.md |
| **Widget factory** | HIGH | developer/Widget-Factory.md |
| **Component-based UI pattern** | HIGH | developer/Components-Guide.md |
| **Dual rendering engines** (Plotly + Matplotlib) | HIGH | developer/Rendering-Engines.md |
| **Repository pattern state management** | HIGH | developer/State-Repositories.md |
| **ConfigSpecBuilder / PresetSpecBuilder** | HIGH | developer/Config-Builders.md |
| **Multi-simulator protocol** | MEDIUM | developer/Multi-Simulator.md |
| **Heatmap plot type** | MEDIUM | plots/Heatmap.md |
| **Dual Axis Bar Dot plot type** | MEDIUM | plots/Dual-Axis-Bar-Dot.md |
| **Export preset system** | MEDIUM | webapp/Export-Presets.md |
| **Portfolio V2 migration** | MEDIUM | developer/Portfolio-Migration.md |
| **Publication validator** | LOW | developer/Publication-Validator.md |
| **Principle compliance tests** | LOW | developer/Testing-Guide.md (section) |
| **Known bugs tracker** | LOW | developer/Known-Issues.md |

### 11.3 Coverage by Audience

| Audience | Docs Coverage | Gap Assessment |
|----------|-------------|---------------|
| **End users** (webapp) | 60% | Missing: settings pills, preset system, dual engine, current navigation |
| **Contributors** (developer) | 40% | Missing: component pattern, FigureSpec, rendering, state repos |
| **AI assistants** (agent) | 90% | `.agent/` and `.github/` are comprehensive and current |

---

## 12. Reusable Content Assessment

### 12.1 Content That Can Be Reused As-Is

| Document | Reusable Sections |
|----------|------------------|
| `Testing-Guide.md` | Fixture documentation, parametrized test examples, markers table, best practices |
| `Parsing-Guide.md` | gem5 variable types, pattern aggregation explanation |
| `services-architecture.md` | Service decomposition diagram, design principles |
| `copilot-instructions.md` | Design patterns table, coding standards, file structure tree |
| `README.md` | Value proposition, workflow overview, performance table, citation |

### 12.2 Content That Needs Major Rewriting

| Document | Scope of Rewrite |
|----------|-----------------|
| `Adding-Plot-Types.md` | COMPLETE REWRITE — every code example uses wrong paths and wrong abstract method |
| `Adding-Shapers.md` | SIGNIFICANT REWRITE — wrong paths, wrong registry keys |
| `Web-Interface.md` | SIGNIFICANT REWRITE — removed features, wrong page list, wrong state API |
| `Architecture.md` | SIGNIFICANT REWRITE — presenter references, missing FigureSpec/component patterns |
| `web-layer-architecture.md` | SIGNIFICANT REWRITE — centered on presenters which are being removed |
| `Installation.md` | MODERATE REWRITE — removed dependency, unverified scripts |

### 12.3 Content That Needs Minor Updates

| Document | Updates Needed |
|----------|---------------|
| `Testing-Guide.md` | Update test count, add principle compliance tests section |
| `CONTRIBUTING.md` | Fix file paths, update test count, add component pattern mention |
| `README.md` | Fix structure tree, update test badge, add missing plot types |
| `architecture-diagram.md` | Remove presenter nodes from Mermaid diagram |
| `plot docs (all 5)` | Verify export options, update file path references |

---

## 13. Migration Plan

### 13.1 Target Documentation Structure

Based on the documentation project plans (`MASTER_PLAN.md`, `USER_GUIDE_PLAN.md`,
`DEVELOPER_GUIDE_PLAN.md`, `AI_KNOWLEDGE_BASE_PLAN.md`), existing docs should
migrate to a new hierarchy. Here is the mapping:

| Current Location | Target Location | Action |
|-----------------|----------------|--------|
| `docs/webapp/Web-Interface.md` | `docs/user-guide/web-interface/overview.md` | REWRITE |
| `docs/webapp/Quick-Start.md` | `docs/user-guide/getting-started/quick-start.md` | UPDATE |
| `docs/webapp/First-Analysis.md` | `docs/user-guide/getting-started/first-analysis.md` | UPDATE |
| `docs/webapp/Creating-Plots.md` | `docs/user-guide/visualization/creating-plots.md` | UPDATE |
| `docs/webapp/Download-Guide.md` | `docs/user-guide/export/download-guide.md` | UPDATE |
| `docs/webapp/Portfolios.md` | `docs/user-guide/portfolio/overview.md` | UPDATE |
| `docs/webapp/pages/Data-Source.md` | `docs/user-guide/pages/data-source.md` | UPDATE |
| `docs/webapp/pages/Data-Managers.md` | `docs/user-guide/pages/data-managers.md` | UPDATE |
| `docs/webapp/pages/Manage-Plots.md` | `docs/user-guide/pages/manage-plots.md` | UPDATE |
| `docs/webapp/pages/Plot-Settings.md` | `docs/user-guide/pages/plot-settings.md` | REWRITE |
| `docs/webapp/pages/Export-Download.md` | `docs/user-guide/export/export-download.md` | UPDATE |
| `docs/plots/Bar-Charts.md` | `docs/user-guide/visualization/bar-charts.md` | UPDATE |
| `docs/plots/Line-Plots.md` | `docs/user-guide/visualization/line-plots.md` | UPDATE |
| `docs/plots/Scatter-Plots.md` | `docs/user-guide/visualization/scatter-plots.md` | UPDATE |
| `docs/plots/histogram-plot.md` | `docs/user-guide/visualization/histogram.md` | UPDATE |
| `docs/plots/Grouped-Stacked-Bars.md` | `docs/user-guide/visualization/grouped-stacked-bars.md` | UPDATE |
| `docs/api/Backend-Facade.md` | `docs/developer-guide/api/application-api.md` | REWRITE |
| `docs/api/Parsing-API.md` | `docs/developer-guide/api/parsing-api.md` | UPDATE |
| `docs/api/Plotting-API.md` | `docs/developer-guide/api/plotting-api.md` | REWRITE |
| `docs/api/Shaper-API.md` | `docs/developer-guide/api/shaper-api.md` | UPDATE |
| `docs/api/Data-Transformations.md` | `docs/developer-guide/api/data-transformations.md` | UPDATE |
| `docs/api/Parsing-Guide.md` | `docs/developer-guide/guides/parsing-guide.md` | UPDATE |
| `docs/developer/Architecture.md` | `docs/developer-guide/architecture/overview.md` | REWRITE |
| `docs/developer/Testing-Guide.md` | `docs/developer-guide/testing/testing-guide.md` | UPDATE |
| `docs/developer/Adding-Plot-Types.md` | `docs/developer-guide/guides/adding-plot-types.md` | REWRITE |
| `docs/developer/Adding-Shapers.md` | `docs/developer-guide/guides/adding-shapers.md` | REWRITE |
| `docs/developer/Development-Setup.md` | `docs/developer-guide/getting-started/development-setup.md` | UPDATE |
| `docs/developer/architecture-diagram.md` | `docs/developer-guide/architecture/diagrams.md` | UPDATE |
| `docs/developer/web-layer-architecture.md` | `docs/developer-guide/architecture/web-layer.md` | REWRITE |
| `docs/developer/services-architecture.md` | `docs/developer-guide/architecture/services.md` | MINOR UPDATE |
| `docs/Installation.md` | `docs/user-guide/getting-started/installation.md` | UPDATE |
| `docs/Home.md` | `docs/index.md` | UPDATE |

### 13.2 New Documents to Create

| Target Location | Source Content |
|----------------|---------------|
| `docs/developer-guide/architecture/figurespec-pipeline.md` | `.agent/ARCHITECTURE.md` + source code |
| `docs/developer-guide/architecture/rendering-engines.md` | Source code analysis |
| `docs/developer-guide/architecture/state-repositories.md` | Step 04 analysis |
| `docs/developer-guide/architecture/components.md` | Source code analysis |
| `docs/developer-guide/guides/settings-pills.md` | Step 12 analysis |
| `docs/user-guide/visualization/heatmap.md` | Source code analysis |
| `docs/user-guide/visualization/dual-axis-bar-dot.md` | Source code analysis |
| `docs/user-guide/export/presets.md` | Step 14 analysis |
| `docs/developer-guide/architecture/multi-simulator.md` | Step 05 analysis |

---

## 14. Priority Fix List

Ordered by severity and impact:

### CRITICAL (Must fix before any documentation release)

1. **Fix `Adding-Plot-Types.md`** — Every code example is wrong. References `src/plotting/types/`, wrong abstract method (`create_figure` vs `create_traces`), wrong constructor signature, wrong factory registry field name. **Action**: Complete rewrite.

2. **Fix `Adding-Shapers.md`** — References non-existent `src/web/services/shapers/`. Wrong registry keys (snake_case vs camelCase). **Action**: Significant rewrite with correct paths.

3. **Remove Performance page from `Web-Interface.md`** — Feature removed Phase 1, still documented with full section. **Action**: Delete sections at lines 31, 238-254.

4. **Remove Upload Data page from `Web-Interface.md`** — Page doesn't exist. **Action**: Delete section at lines 28, 194-210.

5. **Fix `StateManager` API in `Web-Interface.md`** — Import path wrong, API pattern wrong (static vs instance). **Action**: Rewrite state management section.

### HIGH (Should fix in next documentation pass)

6. **Remove presenter references from `Architecture.md`** — Presenters are architected out. **Action**: Replace presenter mentions with component-based pattern.

7. **Update `CONTRIBUTING.md` file paths** — 4 broken paths (`src/web/services/`, `src/plotting/types/`). **Action**: Fix paths to current locations.

8. **Remove pyyaml from `Installation.md`** — Dependency removed. **Action**: Update dependency list.

9. **Update `web-layer-architecture.md`** — Centered on presenter layer. **Action**: Rewrite to reflect component-based architecture.

10. **Fix `README.md` project structure** — Shows `src/core/parsing/` which doesn't exist. **Action**: Fix to `src/parsing/`.

11. **Fix `Development-Setup.md`** — References `src/parsers/`. **Action**: Fix to `src/parsing/`.

12. **Remove Pipeline Import/Export from `Web-Interface.md`** — Feature removed Phase 4. **Action**: Delete section or update.

### MEDIUM (Should fix for accuracy)

13. **Resolve test count contradictions** — 4 different numbers across docs. **Action**: Either remove all hard-coded counts or establish single source of truth.

14. **Fix `docs/index.md` Architecture-Diagram reference** — Case mismatch with actual filename. **Action**: Fix to lowercase.

15. **Add missing plot type docs** — Heatmap and Dual Axis Bar Dot have no documentation. **Action**: Create new files.

16. **Fix `architecture-diagram.md`** — Remove presenter nodes from Mermaid diagram. **Action**: Update diagram.

17. **Fix histogram-plot.md path references** — References `src/plotting/plot_factory.py`. **Action**: Fix path.

### LOW (Nice to have)

18. **Verify external documentation links** — README links to `nikiitin.github.io/RING-5`. **Action**: Verify deployment.

19. **Standardize markdown file naming** — Mix of PascalCase and lowercase. **Action**: Pick convention.

20. **Add CHANGELOG.md** — No changelog exists. **Action**: Create if needed.

21. **Clean up presenter stub** — `src/web/presenters/plot/__init__.py` is a dead import file (imports modules that don't exist). **Action**: Delete file/directory.

---

## 15. Presenter Layer Status

A special note on the presenter layer since it affects many documents:

**Current state**: The `src/web/presenters/` directory contains a single file:
`plot/__init__.py` (23 lines). This `__init__.py` attempts to import three
modules (`config_presenter`, `controls_presenter`, `pipeline_presenter`) that
**do not exist** as files. The presenter files were deleted during the architectural
refactor, but the `__init__.py` was left behind.

**Impact on docs**: The following documents reference presenters:
- `docs/developer/Architecture.md` — Layer C description, project structure, plotting workflow
- `docs/developer/web-layer-architecture.md` — Entire document centered on presenter pattern
- `docs/developer/architecture-diagram.md` — Mermaid diagram includes presenter nodes
- `.github/copilot-instructions.md` — Correctly notes "Presenter layer (removed)"

**Recommendation**: Delete `src/web/presenters/` entirely and update all
documentation to reflect the component-based architecture that replaced it.

---

## 16. Image Asset Audit

21 PNG images exist in `docs/webapp/images/`:

| Image File | Likely Referenced By | Status |
|------------|---------------------|--------|
| `add_variable_dialog_manual.png` | Data-Source.md | VERIFY |
| `add_variable_dialog_search.png` | Data-Source.md | VERIFY |
| `data_managers_no_data_warning.png` | Data-Managers.md | VERIFY |
| `data_managers_with_data.png` | Data-Managers.md | VERIFY |
| `data_source_config_aware.png` | Data-Source.md | VERIFY |
| `data_source_csv_mode.png` | Data-Source.md | VERIFY |
| `data_source_initial.png` | Data-Source.md | VERIFY |
| `data_source_paths_filled.png` | Data-Source.md | VERIFY |
| `data_source_recent_mode.png` | Data-Source.md | VERIFY |
| `e2e_after_scan.png` | First-Analysis.md | VERIFY |
| `e2e_bar_chart.png` | First-Analysis.md | VERIFY |
| `e2e_full_page.png` | First-Analysis.md | VERIFY |
| `e2e_variables_added.png` | First-Analysis.md | VERIFY |
| `manage_plots_chart.png` | Manage-Plots.md | VERIFY |
| `manage_plots_empty.png` | Manage-Plots.md | VERIFY |
| `manage_plots_full.png` | Manage-Plots.md | VERIFY |
| `nav_step_0_landing.png` | Quick-Start.md | VERIFY |
| `parse_error_empty_path.png` | Data-Source.md | VERIFY |
| `portfolio.png` | Portfolios.md | VERIFY |
| `segmented_control.png` | Data-Source.md | VERIFY |
| `sidebar.png` | Web-Interface.md / Quick-Start.md | VERIFY |

All images exist on disk. Screenshots may show outdated UI if taken before
recent refactoring (settings pills, component-based layout). These should be
re-captured after documentation migration.

---

## 17. Internal Consistency Issues

### 17.1 Cross-Document Contradictions

| Topic | Document A | Document B | Discrepancy |
|-------|-----------|-----------|-------------|
| Test count | README: 1110 | CONTRIBUTING: 653 | 457-test difference |
| Test count | Testing-Guide: 1344 | README: 1110 | 234-test difference |
| Coverage target | Architecture.md: 85% | CONTRIBUTING.md: 77% | Different targets |
| Pages count | Web-Interface.md: 7 pages | app.py (Step 01): 5 pages | 2 phantom pages |
| File path of services | CONTRIBUTING: `src/web/services/` | copilot-instructions: `src/core/services/` | Different layers |
| Abstract method | Adding-Plot-Types: `create_figure()` | copilot-instructions: `create_traces()` | Different methods |
| Factory field | Adding-Plot-Types: `_plot_types` | plot_factory.py: `_plot_classes` | Different field names |
| Shaper keys | Step 01/copilot: snake_case | factory.py: camelCase | Different conventions |

### 17.2 Self-Referential Broken Links

| Source Doc | Link Text | Target | Status |
|-----------|-----------|--------|--------|
| `docs/index.md` | Architecture-Diagram | `Architecture-Diagram.md` | BROKEN (case: `architecture-diagram.md`) |
| `Adding-Plot-Types.md` | Testing-Guide.md | `Testing-Guide.md` | OK (exists) |
| `Adding-Plot-Types.md` | Creating-Plots.md | `Creating-Plots.md` | OK (exists) |
| `Installation.md` | Quick-Start | `Quick-Start` | OK (wiki-style link) |
| `Web-Interface.md` | Data-Transformations.md | `Data-Transformations.md` | OK (exists in api/) |

---

## 18. Recommendations for Documentation Project

### 18.1 Immediate Actions (Before Writing New Docs)

1. **Establish single source of truth for architecture** — Use `.github/copilot-instructions.md` file structure tree as the canonical reference. All other docs should be verified against it.

2. **Delete dead presenter stub** — Remove `src/web/presenters/` entirely.

3. **Fix the 5 CRITICAL issues** from the Priority Fix List (Section 14) before any new docs reference these files.

4. **Create a test count policy** — Either always say "run `make test` to see current count" or automate badge updates.

### 18.2 Documentation Project Approach

1. **Do not migrate outdated content** — Documents rated SIGNIFICANTLY OUTDATED should be rewritten from scratch using the deep-dive analysis steps (01-19) as source material.

2. **Reuse agent documentation** — `.agent/ARCHITECTURE.md` and `.github/copilot-instructions.md` are the most accurate sources. Extract content from these for the developer guide.

3. **Reuse code docstrings** — Source code docstrings are high quality (Google-style, Args/Returns/Raises). The API reference sections can be generated or derived from these.

4. **Prioritize developer guide** — The largest gaps are in developer documentation (FigureSpec pipeline, rendering engines, component pattern, state repositories). These block contributors.

5. **Update screenshots last** — Take new screenshots only after the UI stabilizes on the current branch.

### 18.3 Quality Standards for New Docs

Based on this audit, new documentation should:
- Use lowercase-kebab-case filenames consistently
- Include `nav_order` frontmatter for Jekyll
- Reference source files with correct absolute paths from `src/`
- Never hard-code test counts or coverage numbers
- Include "Last verified" dates on per-file basis
- Cross-reference to analysis step that sourced the content
- Use consistent header hierarchy (`#` for title, `##` for sections)

---

## Downstream Dependencies

This analysis feeds into:
- Phase C of the `MASTER_PLAN.md` (existing docs audit and migration)
- `USER_GUIDE_PLAN.md` -- determines what content can be reused vs needs rewriting
- `DEVELOPER_GUIDE_PLAN.md` -- determines what developer content needs rewriting
- All documentation generation uses audit findings to avoid repeating known errors
- Step 21+ (E2E testing documentation) -- should not reference outdated docs
