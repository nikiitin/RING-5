# Agent Prompt: Unified Engine UI & Download Overhaul

> **Branch**: `005/unified-engine-ui-v2`
> **Base commit**: `0c2c56d` on `004/engine-agnostic-viz`
> **Total steps**: 39 (5 phases + architecture doc update)
> **Total commits**: 39 step commits + 5 phase review commits + 1 final review commit = 45
> **Estimated lines**: +2,000 new / −3,800 deleted (net −1,800)
> **Test baseline**: 3,328 tests (all must remain green throughout)
> **Testing constraints**: Minimal memory, no threading in new code, function-scoped fixtures by default
> **Quality gates**: Per-step quality review, PR-level phase review, deep final review before main merge

---

## 📍 PROGRESS TRACKER

> **Current position**: Phase 3, Step 24 (not yet started)
> **Last completed step**: Phase 3, Step 23
>
> | Phase | Steps | Status |
> |-------|-------|--------|
> | Phase 0 — Foundation | Steps 0–3 | ✅ Complete |
> | Phase 1 — Spec Layer | Steps 4–12 + Review | ✅ Complete |
> | Phase 2 — Wiring & Export | Steps 13–22 + Review | ✅ Complete |
> | Phase 3 — Pills UI Reorganization | Steps 23–31 + Review | 🔄 Step 23 done, Step 24 next |
> | Phase 4 — Delete Old Code | Steps 32–37 + Review | ⬜ Not started |
> | Phase 5 — Final Review | Steps 38–39 | ⬜ Not started |

---

## ⛔ ABSOLUTE RULES — READ BEFORE ANYTHING

1. **One commit per step + quality review.** Every step below gets its own commit with message format: `[Phase N / Step M] <description>`. Use `git add -A && git commit -m "..."`. **After each commit**, write a brief summary covering:
   - What was done and why (1–3 sentences)
   - **Coding quality review**: Are type hints complete? Are naming conventions consistent? Is error handling adequate? Any code smells?
   - **Programming behavior review**: Did you follow TDD? Did you maintain layer separation? Did you avoid anti-patterns? Any shortcuts taken that need revisiting?
2. **Tests must pass before every commit.** Run `./python_venv/bin/pytest tests/ -q -x --tb=short` after every step. If tests fail, fix them before committing.
3. **Type checking after every step.** Run `./python_venv/bin/mypy src/core/visualization/ --strict --no-error-summary 2>&1 | head -20`. Fix any errors.
4. **Format after every step.** Run `./python_venv/bin/black src/ tests/ -q`.
5. **Phase review after each phase.** After the last step of each phase, perform a **PR-level review** (see Phase Review Protocol below) + full test suite + mypy + flake8. Fix ALL issues before proceeding.
6. **NEVER use `inplace=True`** on DataFrames.
7. **NEVER import Streamlit in Layer B (domain) or Layer A (data).** Only in Layer C (presentation/web).
8. **NEVER use `plt.show()` or the pyplot state machine.** Always use OO API: `fig, ax = plt.subplots(...)`.
9. **NEVER leave `Any` type annotations** where a concrete type is known. Use `TYPE_CHECKING` imports for circular dependency resolution.
10. **NEVER modify `interactive_plotly_chart` component** — it is sacrosanct.
11. **`.gitignore` blocks `*.txt`** — use `.md` for all context/documentation files.
12. **Test with MINIMAL MEMORY.** Use `--tb=short` and `-q` flags. Avoid loading entire datasets when a fixture slice suffices. Prefer small focused fixtures over large data. Do NOT cache large objects in module scope. Use `pytest.fixture(scope="function")` as default, only escalate to `session` when truly needed.
13. **NO THREADING in tests or implementation.** Do not use `threading`, `multiprocessing`, or `concurrent.futures` for any new code in this plan. All new visualization/export code must be single-threaded and synchronous. The existing async parsing infrastructure is untouched — this rule applies only to the code created or modified by this plan.
14. **Architecture documentation update.** After ALL steps are complete and the final review passes, update `.agent/ARCHITECTURE.md` with all architectural changes made during this plan (new modules, deleted modules, changed patterns, new data flow).
15. **Zero tolerance for backward compatibility with old/deprecated code.** This rule applies **retroactively to all previous steps** and to every step going forward:
    - **No compatibility shims.** If old code, old patterns, or deprecated APIs are encountered during any step, they must be removed or replaced on the spot — not wrapped, not kept "for now."
    - **Mandatory dead-code cleanup.** Everything that is not actively used by the current architecture must be deleted. Unused imports, unreachable branches, orphaned helpers, stale test utilities — all go.
    - **Consistency with new features.** When a new pattern or module is introduced (e.g., `FigureSpec`, `EngineManager`, `PresetApplicator`), all remaining code that still uses the old pattern it replaces must be migrated in the same step or the immediately following step. There is no grace period.
    - **Breaking old code is beneficial.** If removing deprecated code causes errors elsewhere, that is a *feature*, not a bug — it surfaces every caller that still depends on the old path and forces an immediate update. Fix the callers; do not re-introduce the old code.
    - **No "optional" old paths.** Do not maintain two ways of doing the same thing (old + new). One canonical path only.
    - **Applies during Phase Reviews.** Every Phase Review must include a sweep for lingering old-architecture code and flag it for removal before proceeding.

### Per-Step Commit Protocol

After completing each step, before moving to the next:

1. Run validation commands (tests, mypy, black)
2. Commit with format: `[Phase N / Step M] <description>`
3. Write a **Step Review** containing:
   - **Summary**: What was implemented/changed and why
   - **Coding Quality**: Type completeness, naming conventions, error handling, code smells, DRY compliance
   - **Behavior Review**: TDD adherence, layer separation, pattern consistency, any debt introduced
   - **Metrics**: Lines added/removed, test count delta

### Phase Review Protocol (PR-Level)

At the end of each phase, conduct a thorough review as if you were reviewing a GitHub Pull Request:

1. **Diff review**: Go through EVERY file changed in the phase. Check for:
   - Unused imports
   - Dead code or commented-out code
   - Inconsistent naming (camelCase vs snake_case)
   - Missing docstrings on public APIs
   - Overly broad exception handling
   - Magic numbers or hardcoded strings that should be constants
2. **Architectural review**: Verify layer boundaries are respected. No domain → UI leaks, no data → presentation leaks.
3. **Test adequacy**: Check that every new public function/method has at least one test. Check edge cases.
4. **Type safety**: Run `mypy --strict` on ALL modified directories, not just `src/core/visualization/`.
5. **Performance**: Ensure no O(n²) patterns, no unnecessary copies, no memory leaks (unclosed figures, unbounded caches).
6. **Consistency**: Naming, docstring style, import ordering should be uniform across all new/modified files.
7. **Backward-compatibility sweep (Rule 15)**: Scan all files touched in the phase for remnants of old/deprecated patterns. If any code still uses a pattern that was superseded by this plan (old applicator methods, old export paths, old config keys, deprecated APIs), it must be removed or migrated before the phase is considered complete.
8. **Write a PR-level summary** with: changes overview, risk areas, test coverage assessment, and any caveats for the reviewer.

---

## 🧬 Codebase Architecture Summary

You are working in RING-5, a scientific data analysis tool for gem5 simulator output. The visualization stack has these key layers:

### Core Visualization Module (`src/core/visualization/`)
- **`figure_spec.py`** (205 lines) — Top-level `FigureSpec` frozen dataclass. Contains `DimensionsSpec`, `MarginsSpec`, `SeparatorSpec`. **5 fields use `Any` that must be fixed in Step 0.**
- **`typography_spec.py`** (71 lines) — `TypographySpec` with per-element font sizes (title, xlabel, ylabel, ticks, yticks, text) + bold flags. Uses sentinel value `-1` for inheritance.
- **`axis_spec.py`** (120 lines) — `AxisSpec` (single axis: label, ticks, range, scale, grid, categories, dtick, automargin) + `AxesSpec` container (x, y, y2).
- **`legend_spec.py`** (161 lines) — `LegendSpec` (orientation, position, appearance, spacing via `LegendSpacingSpec`) with roles: primary/secondary/boxed.
- **`trace_spec.py`** (103 lines) — `TraceSpec` base + `BarTraceSpec`, `LineTraceSpec`, `ScatterTraceSpec`.
- **`annotation_spec.py`** (79 lines) — `AnnotationSpec` + `ReferenceLineSpec`.
- **`resolvers.py`** (205 lines) — Sentinel resolution: fills `-1` values via typography chains, legend inheritance, y2→y fallback.

### Connectors (`src/core/visualization/connectors/`)
- **`plotly_connector.py`** (255 lines) — `FigureSpecToPlotly.apply(spec, fig)`. Implements: dimensions, backgrounds, title, xaxis, yaxis, y2axis, legends. **Missing**: data labels, series styling, reference lines, axis colors, color palette, hatching, hover, stripes, auto-contrast, separators, font family.
- **`matplotlib_connector.py`** (307 lines) — `FigureSpecToMatplotlib.apply(spec, ax)`. Implements: title, axis labels, axis ticks, axis ranges, grids, legends, LaTeX escaping, `create_figure()`. **Missing**: backgrounds, annotations, reference lines, separators, font family, data labels, color palette, hatching, constrained_layout.
- **`builders.py`** (593 lines) — Three builders:
  - `PlotlyFigureSpecBuilder.from_plotly(fig, config)` — extracts spec from existing Plotly figure
  - `PresetSpecBuilder.from_preset(preset)` — builds from LaTeXPreset dict
  - `ConfigSpecBuilder.from_config(config, plot_type)` — builds from flat UI config dict. **Missing**: data labels, annotations, separators, bold flags, y2-axis, reference lines, ~30 unmapped keys.

### Widgets (`src/core/visualization/widgets/`)
- **`widget_def.py`** (440 lines) — 10 `WidgetSection` constants, ~50 widget instances. **Only 18 of 50 have `spec_path` set.** Sections: `LAYOUT_MARGINS`, `LAYOUT_DIMENSIONS`, `TYPOGRAPHY`, `LEGEND_POSITION`, `LEGEND_APPEARANCE`, `LEGEND_SIZING`, `LEGEND` (aggregate), `BACKGROUNDS`, `AXIS_COLORS`, `DATA_LABELS`.
- **`config_bridge.py`** (155 lines) — Bidirectional FigureSpec ↔ flat config dict via `spec_path`.
- **`widget_renderer.py`** (199 lines) — Streamlit widget rendering from `WidgetDef` definitions.

### StyleApplicator (`src/web/pages/ui/plotting/styles/applicator.py`, 654 lines)
The Plotly-side styling engine. Builds `FigureSpec` via `ConfigSpecBuilder` (stored as `self.last_spec`) but then applies Plotly styling **directly** via `fig.update_layout()` calls — NOT through the connector. Key methods:
- `apply_styles()` — orchestrator
- `_apply_dimensions_and_margins()`, `_apply_backgrounds()`, `_apply_axes_styling()`, `_apply_xaxis_label_overrides()`, `_apply_axis_colors()`, `_apply_titles()`, `_apply_data_labels()`, `_apply_conditional_labels()`, `_apply_auto_contrast()`, `_apply_legend_layout()`, `_apply_series_styling()`, `_apply_yaxis_title_annotation()`

### Plot Renderer (`src/web/pages/ui/plotting/plot_renderer.py`, 1,242 lines)
- `_render_download_button()` (L240–L1227, **~987 lines**) — The export monolith. Renders the entire "Export for LaTeX" expander with 5 nested expanders, preset selector, format selector, preview, and download. All values assembled into a `preset_to_use` dict.
- Uses `interactive_plotly_chart()` (custom component) for rendering — **never replace this**.

### Export Infrastructure (`src/web/pages/ui/plotting/export/`, ~3,100 lines total)
- **`latex_export_service.py`** (175 lines) — Facade: `export()`, `list_presets()`, `generate_preview()`
- **`converters/impl/matplotlib_converter.py`** (910 lines) — Plotly→matplotlib→PDF/PGF/EPS
- **`converters/impl/layout_applier.py`** (891 lines) — Applies layout to matplotlib. **Duplicates much of `FigureSpecToMatplotlib`**.
- **`converters/impl/layout_mapper.py`** (430 lines) — Plotly→dict→matplotlib mapping
- **`presets/preset_schema.py`** (157 lines) — `LaTeXPreset` TypedDict (~50 fields)
- **`presets/preset_manager.py`** (283 lines) — YAML loading, validation
- **`presets/latex_presets.yaml`** (~250 lines) — 13 presets (ISCA, MICRO, ASPLOS, Nature, etc.)

### Portfolio System (`src/core/services/data_services/portfolio_service.py`)
Saves portfolios as JSON with raw flat `Dict[str, Any]` config per plot. Does NOT go through `FigureSpec.to_dict()` — configs are Plotly-vocabulary-dependent.

### Session State (`src/core/state/state_manager.py`, 186 lines)
`StateManager` Protocol with NO engine/visualization-specific state keys. Visualization state stored per-plot in `plot.config` (flat dict).

### Custom Plotly Component
`interactive_plotly_chart()` in `src/web/pages/ui/components/interactive_plot.py` — wraps Plotly.js with event capture for legend dragging. **Must not be modified or replaced.**

---

## 📚 Knowledge Base: Visualization Best Practices

These principles MUST be applied throughout all phases:

### Matplotlib Best Practices
1. **ALWAYS use OO API**: `fig, ax = plt.subplots(...)`. NEVER use `plt.plot()`, `plt.xlabel()`, etc.
2. **Use `layout='constrained'`** (not `constrained_layout=True`, which is deprecated). This is Matplotlib 3.x recommended for complex layouts with external legends and multi-axis.
3. **PGF backend for LaTeX**: `fig.savefig(buf, format="pgf")` produces native LaTeX commands. Fonts match the document automatically. Configure via `rcParams`:
   ```python
   plt.rcParams.update({
       "pgf.texsystem": "xelatex",  # or "pdflatex", "lualatex"
       "pgf.preamble": r"\usepackage{...}",
       "pgf.rcfonts": True,
   })
   ```
4. **Always close figures**: After `st.pyplot(fig)`, call `plt.close(fig)` to free memory. Or use `st.pyplot(fig, clear_figure=True)`.
5. **Use `rcParams` context managers**: `with plt.rc_context({...}):` for temporary style changes.
6. **`bbox_inches='tight'`** on `savefig()` to avoid clipping.
7. **Data-ink ratio**: Remove top/right spines (`ax.spines['top'].set_visible(False)`), minimize gridlines, no chartjunk.

### Plotly Best Practices
1. **Plotly Templates for theming**: Create `go.layout.Template` objects with layout defaults and register with `pio.templates["ring5_base"]`. Apply via `fig.update_layout(template="ring5_base")`. Combine with `"plotly_white+ring5_isca"`.
2. **Template structure**: `template.layout` sets layout defaults. `template.data.bar = [go.Bar(marker=dict(...))]` sets trace defaults. Templates are composable.
3. **Kaleido v1 for static export**: `fig.to_image(format="png", width=w, height=h, scale=2)` returns bytes. Supported: PNG, JPEG, WebP, SVG, PDF. Kaleido v1 uses system Chrome (no bundled browser).
4. **Magic underscore notation**: `go.Layout(title_font_size=24)` equals `go.Layout(title=dict(font=dict(size=24)))`.
5. **Graph Objects only**: Never use Plotly Express for this project. Always `go.Figure()`, `go.Bar()`, `go.Scatter()`.
6. **Streamlit theming**: `st.plotly_chart(fig, theme=None)` disables Streamlit theme override — use when custom template is applied.

### Streamlit `st.pills` API
```python
selected = st.pills(
    "Label",
    options=["A", "B", "C"],
    selection_mode="single",  # or "multi"
    format_func=lambda x: f":material/icon: {x}",  # Material icons
    key="unique_key",
    default=None,  # or specific value
)
```
- Returns selected value (single mode) or list (multi mode), or `None`.
- Supports Material Design icons via `:material/icon_name:` in labels.
- `width="stretch"` to fill container.

### Publication Standards by Venue
| Venue | Width | Height | DPI | Font Family | Font Base |
|-------|-------|--------|-----|-------------|-----------|
| IEEE single column | 3.5" | 2.625" | 300 | serif | 8pt |
| IEEE double column | 7.0" | 5.25" | 300 | serif | 8pt |
| ISCA/MICRO/ASPLOS/HPCA | 3.5" | 2.5" | 300 | serif | 8pt |
| Nature | 3.5" | 3.5" | 600 | Arial | 7pt |
| Science | 3.5" | 2.5" | 600 | sans-serif | 7pt |
| Poster | 10.0" | 7.0" | 150 | sans-serif | 24pt |
| Slides | 8.0" | 4.5" | 150 | sans-serif | 18pt |

### Font Size Guidelines
- Tick labels: 7–8pt minimum
- Axis labels: 8–9pt
- Title: 9–10pt
- Legend: 7–8pt
- Data annotations: 6–7pt

### Colorblind-Safe Defaults
**Wong palette** (8 colors, optimized for discrete categories):
```python
WONG_PALETTE = [
    "#000000",  # Black
    "#E69F00",  # Orange
    "#56B4E9",  # Sky Blue
    "#009E73",  # Bluish Green
    "#F0E442",  # Yellow
    "#0072B2",  # Blue
    "#D55E00",  # Vermilion
    "#CC79A7",  # Reddish Purple
]
```
Additional built-in palettes: Viridis (continuous), Plasma (continuous), seaborn-colorblind (categorical).
Minimum contrast ratio: 4.5:1 for text on colored backgrounds.

### Data-Ink Ratio Principles (Tufte)
- Remove non-data-ink: decorative borders, shadows, 3D effects
- Remove top/right spines by default
- Use gridlines sparingly (light gray, thin)
- Prefer direct labeling over legends when practical
- White backgrounds for print; minimal chrome

---

## Phase 0: Foundation — Type Safety, Rules & Knowledge Base (Steps 0–3)

**Goal**: Fix `Any` type erosion, update agent rules with book knowledge, create reference knowledge file.

### Step 0 — Fix `Any` types in `figure_spec.py`

**File**: `src/core/visualization/figure_spec.py`

**Problem**: 5 fields use `Any` to avoid circular imports:
```python
typography: Any = None       # Should be Optional[TypographySpec]
axes: Any = None             # Should be Optional[AxesSpec]
legends: List[Any] = ...     # Should be List[LegendSpec]
traces: List[Any] = ...      # Should be List[TraceSpec]
annotations: List[Any] = ... # Should be List[AnnotationSpec]
```

**Solution**: Use `TYPE_CHECKING` guard + string annotations:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.visualization.typography_spec import TypographySpec
    from src.core.visualization.axis_spec import AxesSpec
    from src.core.visualization.legend_spec import LegendSpec
    from src.core.visualization.trace_spec import TraceSpec
    from src.core.visualization.annotation_spec import AnnotationSpec

@dataclass
class FigureSpec:
    typography: Optional[TypographySpec] = None
    axes: Optional[AxesSpec] = None
    legends: List[LegendSpec] = field(default_factory=list)
    traces: List[TraceSpec] = field(default_factory=list)
    annotations: List[AnnotationSpec] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)  # str values, not Any
```

**Keep** the `__post_init__` lazy imports for runtime — they are needed because `from __future__ import annotations` makes all annotations strings. The runtime code in `__post_init__` that imports and creates defaults is still necessary.

**Validation**: `./python_venv/bin/mypy src/core/visualization/figure_spec.py --strict` — zero errors.

**Commit**: `[Phase 0 / Step 0] Fix Any types in FigureSpec with TYPE_CHECKING guards`

---

### Step 1 — Create visualization best practices knowledge file

**File**: `.agent/context/visualization-best-practices.md` (NOT `.txt` — blocked by `.gitignore`)

**Content**: Create the directory `.agent/context/` if it doesn't exist. Write a comprehensive reference containing:

1. **Publication rcParams** — figure sizes per venue (table above), DPI rules (screen 100-150, print 300+, Nature/Science 600)
2. **Font size guidelines** — per element minimums by venue
3. **Colorblind-safe palettes** — Wong palette hex values, Viridis/Plasma references, contrast ratio rules
4. **Matplotlib patterns** — OO API only, `layout='constrained'`, `bbox_inches='tight'`, `plt.close(fig)`, `rc_context`, PGF backend config
5. **Plotly patterns** — GO only, magic underscore, template system, Kaleido v1 export, `fig.to_image()` vs `fig.write_image()`
6. **Data-ink ratio** — Tufte principles: remove spines, minimal gridlines, no chartjunk, direct labeling
7. **Hatching patterns** — for B&W-friendly differentiation: `['/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*']`
8. **Memory discipline** — matplotlib figure lifecycle, `plt.close(fig)`, `clear_figure=True` in `st.pyplot()`

**Commit**: `[Phase 0 / Step 1] Create visualization best practices knowledge file`

---

### Step 2 — Update rule 002 §4 "Plotting Best Practices"

**File**: `.agent/rules/002-data-science-mastery.md`

**Current §4** (around line 64-70): Very brief — just 4 bullet points about font sizes, vector formats, Plotly GO, and labels.

**Replace with expanded §4**:
```markdown
## 4. Plotting Best Practices

### 4.1 Matplotlib (OO API — MANDATORY)
- **ALWAYS** use `fig, ax = plt.subplots(layout='constrained')`. NEVER use pyplot state machine (`plt.plot()`, `plt.xlabel()`).
- **`layout='constrained'`** over `tight_layout()` — more robust for external legends, multi-axis, colorbars.
- **PGF backend for LaTeX**: `fig.savefig(buf, format="pgf", backend="pgf")` with `pgf.texsystem="xelatex"` by default.
- **Always close figures**: `plt.close(fig)` after `st.pyplot(fig)` or use `clear_figure=True`. Unclosed figures leak memory.
- **rcParams context managers**: `with plt.rc_context({"font.size": 8}):` for temporary overrides without global mutation.
- **`bbox_inches='tight'`** on all `savefig()` calls to prevent label clipping.
- **Data-ink ratio**: Remove top/right spines by default, minimize gridlines, no 3D effects or chartjunk.

### 4.2 Plotly (Graph Objects — MANDATORY)
- **Custom Templates** for theming: `pio.templates["ring5_base"] = go.layout.Template(layout=go.Layout(…))`. Apply via `fig.update_layout(template="ring5_base")`.
- **Template composition**: `"plotly_white+ring5_isca"` layers templates. Custom always on top of base.
- **Kaleido v1** for static export: `fig.to_image(format="png", scale=2)`. Uses system Chrome. No Orca.
- **Magic underscore**: Prefer `title_font_size=24` over nested dicts. But use explicit dicts in templates for clarity.
- **Graph Objects only**: `go.Figure()`, `go.Bar()`, `go.Scatter()`. Never Plotly Express.
- **Streamlit integration**: `st.plotly_chart(fig, theme=None)` when using custom templates to prevent Streamlit overrides.

### 4.3 Accessibility & Publication Quality
- **Colorblind-safe palettes**: Wong palette as default (8 discrete colors). Viridis for continuous. 4.5:1 contrast minimum.
- **Font sizing by venue**: Ticks 7-8pt, labels 8-9pt, titles 9-10pt, legends 7-8pt.
- **Vector formats mandatory**: PDF/SVG/PGF for print. Raster at 2× scale minimum (scale=2 in Kaleido).
- **DPI**: Screen 100-150, print 300+, Nature/Science 600.
- **Sans-serif for screen, serif for LaTeX** by default.
```

**Commit**: `[Phase 0 / Step 2] Update rule 002 §4 with comprehensive plotting best practices`

---

### Step 3 — Add §9 "Visualization Engine Architecture" to rule 001

**File**: `.agent/rules/001-architecture-standards.md`

**Add new section before the closing status block**:
```markdown
## 9. Visualization Engine Architecture

### 9.1 FigureSpec as Single Source of Truth
- `FigureSpec` is the canonical representation of a plot's styling. ALL rendering flows through it.
- Building: `ConfigSpecBuilder.from_config(config) → resolve_spec(spec) → FigureSpec`
- Applying: `FigureSpecToPlotly.apply(spec, fig)` or `FigureSpecToMatplotlib.apply(spec, ax)`

### 9.2 Engine Connectors are Stateless Translators
- `FigureSpecToPlotly` and `FigureSpecToMatplotlib` are pure functions. No state, no side effects beyond the figure mutation.
- Same `FigureSpec` must produce visually equivalent output in both engines.

### 9.3 Plotly Templates Map 1:1 to LaTeX Presets
- Each LaTeX preset (ISCA, MICRO, etc.) has a corresponding Plotly template: `"ring5_isca"`, `"ring5_micro"`.
- Application: `fig.update_layout(template="plotly_white+ring5_isca")`

### 9.4 Interactive Plotly Component is Sacrosanct
- `interactive_plotly_chart` in `src/web/pages/ui/components/interactive_plot.py` must NEVER be replaced with `st.plotly_chart`.
- It captures `relayoutData` for legend position persistence.

### 9.5 Memory Discipline
- Every `matplotlib.figure.Figure` must be closed after rendering: `plt.close(fig)`.
- In Streamlit: use `st.pyplot(fig, clear_figure=True)`.
- Store figure bytes for download, not figure objects.
```

**Commit**: `[Phase 0 / Step 3] Add §9 Visualization Engine Architecture to rule 001`

---

## Phase 1: FigureSpec Full Coverage (Steps 4–12)

**Goal**: Make `FigureSpec` a complete superset of every styling feature currently in `StyleApplicator` (654 lines) and `_render_download_button` (987 lines), enabling the connectors to fully replace them.

### Step 4 — Add `DataLabelSpec`

**Create**: `src/core/visualization/data_label_spec.py`

Create a frozen dataclass matching the 12 fields in `DATA_LABELS` widget section of `widget_def.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass(frozen=True)
class DataLabelSpec:
    """Specification for data labels on plot traces."""
    enabled: bool = False
    color_mode: Literal["auto", "custom", "contrast"] = "auto"
    custom_color: str = "#000000"
    font_size: int = 10
    font_weight: Literal["normal", "bold"] = "normal"
    rotation: int = 0
    position: Literal["inside", "outside", "auto"] = "auto"
    format_string: str = ""
    decimal_places: int = 2
    prefix: str = ""
    suffix: str = ""
    auto_contrast: bool = True
```

Add `data_labels: Optional[DataLabelSpec] = None` to `FigureSpec`.

**Tests**: `tests/unit/core/visualization/test_data_label_spec.py`
- `test_default_values` — verify all defaults
- `test_to_dict_from_dict_roundtrip` — serialize/deserialize
- `test_frozen` — cannot mutate
- `test_custom_values` — constructor with all fields

**Commit**: `[Phase 1 / Step 4] Add DataLabelSpec dataclass`

---

### Step 5 — Add `SeriesStyleSpec`

**Create**: `src/core/visualization/series_style_spec.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SeriesStyleSpec:
    """Per-trace styling overrides."""
    line_width: float = 2.0
    marker_size: int = 8
    marker_symbol: str = "circle"
    bar_border_width: float = 0.0
    bar_border_color: str = "#000000"
    opacity: float = 1.0
    hatching_pattern: str = ""  # Empty = no hatching. Values: /, \\, |, -, +, x, o, O, ., *
```

Add `series_styles: List[SeriesStyleSpec] = field(default_factory=list)` to `FigureSpec`.

**Tests**: Similar pattern to Step 4.

**Commit**: `[Phase 1 / Step 5] Add SeriesStyleSpec dataclass`

---

### Step 6 — Add missing scalar fields to `FigureSpec`

**File**: `src/core/visualization/figure_spec.py`

Add these fields to `FigureSpec`:
```python
color_palette: List[str] = field(default_factory=lambda: [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
])  # Wong colorblind-safe palette
hatching_sequence: List[str] = field(default_factory=lambda: [
    "/", "\\", "|", "-", "+", "x", "o", "O",
])
reference_lines: List[ReferenceLineSpec] = field(default_factory=list)
hovermode: str = "x unified"
enable_stripes: bool = False
show_error_bars: bool = False
```

**Note**: `ReferenceLineSpec` already exists in `annotation_spec.py`. Import it properly.

**Tests**: Verify defaults, roundtrip serialization, that `reference_lines` accepts `ReferenceLineSpec` instances.

**Commit**: `[Phase 1 / Step 6] Add missing scalar fields to FigureSpec`

---

### Step 7 — Extend `AxisSpec`

**File**: `src/core/visualization/axis_spec.py`

Add to `AxisSpec`:
```python
tick_font_color: str = ""      # Empty = inherit from theme
label_standoff: int = -1       # Sentinel: -1 = auto
title_vshift: float = 0.0      # Vertical shift for title annotation
axis_line_color: str = ""      # Empty = inherit
axis_line_width: float = 1.0
```

**Tests**: Verify defaults, roundtrip, resolver handles new sentinels.

**Commit**: `[Phase 1 / Step 7] Extend AxisSpec with missing fields`

---

### Step 8 — Extend `LegendSpec`

**File**: `src/core/visualization/legend_spec.py`

Add to `LegendSpec`:
```python
col_width: float = -1.0            # Sentinel: -1 = auto
order: Literal["normal", "reversed"] = "normal"
trace_distribution: str = ""       # Comma-separated trace indices, empty = all
```

**Tests**: Verify defaults, roundtrip.

**Commit**: `[Phase 1 / Step 8] Extend LegendSpec with col_width, order, trace_distribution`

---

### Step 9 — Complete `ConfigSpecBuilder`

**File**: `src/core/visualization/connectors/builders.py`

Map ALL currently-unmapped config keys in `ConfigSpecBuilder.from_config()`:

**Data labels** (11 keys):
- `show_values` → `data_labels.enabled`
- `value_text_color_mode` → `data_labels.color_mode`
- `value_text_custom_color` → `data_labels.custom_color`
- `text_font_size` → `data_labels.font_size`
- `value_text_weight` → `data_labels.font_weight`
- `value_text_rotation` → `data_labels.rotation`
- `value_text_position` → `data_labels.position`
- `value_format_string` → `data_labels.format_string`
- `value_decimal_places` → `data_labels.decimal_places`
- `value_prefix` → `data_labels.prefix`
- `value_suffix` → `data_labels.suffix`

**Axis colors** (4 keys):
- `axis_color` → `axes.xaxis.axis_line_color`, `axes.yaxis.axis_line_color`
- `grid_color` → `axes.xaxis.tick_font_color` (or create grid_color field)

**Series styling** (3 keys):
- `bar_border_width` → `series_styles[*].bar_border_width`
- `marker_size` → `series_styles[*].marker_size`
- `line_width` → `series_styles[*].line_width`

**Reference lines** (5 keys):
- `reference_lines` → `reference_lines` (list serialization)

**Ordering** (2 keys):
- `legend_traceorder` → `legends[0].order`

**Other**:
- `shapes` → `separator` config
- `show_error_bars` → `show_error_bars`
- `color_palette` → `color_palette`
- `hatching_enabled` → `hatching_sequence`

Also wire `spec_path` on the corresponding `WidgetDef` instances in `widget_def.py`.

**Tests**: For each new mapping, create config dict → build spec → verify field value.

**Commit**: `[Phase 1 / Step 9] Complete ConfigSpecBuilder with ~30 new config key mappings`

---

### Step 10 — Complete `FigureSpecToPlotly`

**File**: `src/core/visualization/connectors/plotly_connector.py`

Add these methods to `FigureSpecToPlotly`:

```python
@staticmethod
def _apply_data_labels(spec: FigureSpec, fig: go.Figure) -> None:
    """Apply data label annotations on bars/points."""
    # texttemplate, textposition, textfont, textangle

@staticmethod
def _apply_series_styling(spec: FigureSpec, fig: go.Figure) -> None:
    """Apply per-trace line_width, marker, opacity."""

@staticmethod
def _apply_reference_lines(spec: FigureSpec, fig: go.Figure) -> None:
    """Add horizontal/vertical reference lines via fig.add_shape()."""

@staticmethod
def _apply_axis_colors(spec: FigureSpec, fig: go.Figure) -> None:
    """Apply tick/label/line colors per axis."""

@staticmethod
def _apply_xaxis_label_overrides(spec: FigureSpec, fig: go.Figure) -> None:
    """Custom tick text via tickmode='array'."""

@staticmethod
def _apply_auto_contrast(spec: FigureSpec, fig: go.Figure) -> None:
    """Set text color based on background luminance (bar charts)."""

@staticmethod
def _apply_multi_legend_trace_distribution(spec: FigureSpec, fig: go.Figure) -> None:
    """Assign traces to legend/legend2/legend3."""

@staticmethod
def _apply_color_palette(spec: FigureSpec, fig: go.Figure) -> None:
    """Set colorway from spec.color_palette."""

@staticmethod
def _apply_stripes(spec: FigureSpec, fig: go.Figure) -> None:
    """Alternating row background shapes."""

@staticmethod
def _apply_hovermode(spec: FigureSpec, fig: go.Figure) -> None:
    """Set hovermode from spec."""

@staticmethod
def _apply_font_family(spec: FigureSpec, fig: go.Figure) -> None:
    """Set global font family."""

@staticmethod
def _apply_separator_lines(spec: FigureSpec, fig: go.Figure) -> None:
    """Group separator vertical lines."""

@staticmethod
def _apply_hatching(spec: FigureSpec, fig: go.Figure) -> None:
    """Pattern fills for bar traces."""
```

Wire all into `apply()` orchestrator. Look at `StyleApplicator`'s `_apply_*` methods for exact Plotly API calls to replicate.

**Tests**: For each method, create mock `go.Figure()`, apply spec, verify `fig.layout` / `fig.data` properties.

**Commit**: `[Phase 1 / Step 10] Complete FigureSpecToPlotly with ~16 new feature methods`

---

### Step 11 — Complete `FigureSpecToMatplotlib`

**File**: `src/core/visualization/connectors/matplotlib_connector.py`

Add these methods:

```python
@staticmethod
def _apply_backgrounds(spec: FigureSpec, fig: Figure, ax: Axes) -> None:
    """fig.patch.set_facecolor(), ax.set_facecolor()"""

@staticmethod
def _apply_annotations(spec: FigureSpec, ax: Axes) -> None:
    """ax.annotate() for bar values, group labels, boxed annotations"""

@staticmethod
def _apply_reference_lines(spec: FigureSpec, ax: Axes) -> None:
    """ax.axhline() / ax.axvline()"""

@staticmethod
def _apply_separators(spec: FigureSpec, ax: Axes) -> None:
    """Vertical lines between groups"""

@staticmethod
def _apply_font_family(spec: FigureSpec) -> Dict[str, Any]:
    """Return rcParams dict for font.family context manager"""

@staticmethod
def _apply_data_labels(spec: FigureSpec, ax: Axes) -> None:
    """ax.bar_label() or manual ax.text()"""

@staticmethod
def _apply_color_palette(spec: FigureSpec) -> Dict[str, Any]:
    """Return rcParams for axes.prop_cycle"""

@staticmethod
def _apply_hatching(spec: FigureSpec, ax: Axes) -> None:
    """Bar hatching patterns"""
```

Update `create_figure()` to use `layout='constrained'`:
```python
@staticmethod
def create_figure(spec: FigureSpec) -> Tuple[Figure, Axes]:
    fig, ax = plt.subplots(
        figsize=(spec.dimensions.width, spec.dimensions.height),
        dpi=spec.dimensions.dpi,
        layout='constrained',
    )
    return fig, ax
```

Look at `layout_applier.py` (891 lines) for exact matplotlib API calls to replicate.

**Tests**: For each method, create `fig, ax = plt.subplots()`, apply spec, verify properties. Always `plt.close(fig)` in teardown.

**Commit**: `[Phase 1 / Step 11] Complete FigureSpecToMatplotlib with ~12 new feature methods`

---

### Step 12 — Create `PlotlyTemplateFactory`

**Create**: `src/core/visualization/connectors/plotly_templates.py`

```python
"""Plotly Template factory — maps LaTeX presets to Plotly templates."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict

WONG_PALETTE = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

def create_base_template() -> go.layout.Template:
    """Base RING-5 template: colorblind-safe, data-ink optimized."""
    return go.layout.Template(
        layout=go.Layout(
            colorway=WONG_PALETTE,
            font=dict(family="Arial, sans-serif", size=10, color="#333333"),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=True, gridcolor="#E5E5E5", gridwidth=1,
                showline=True, linecolor="#333333", linewidth=1,
                ticks="outside", tickcolor="#333333",
                title_standoff=15, automargin=True,
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=True, gridcolor="#E5E5E5", gridwidth=1,
                showline=True, linecolor="#333333", linewidth=1,
                ticks="outside", tickcolor="#333333",
                title_standoff=15, automargin=True,
                zeroline=False,
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#CCCCCC", borderwidth=1,
            ),
            margin=dict(l=60, r=20, t=40, b=60),
        ),
    )

def create_preset_template(preset_name: str, preset_info: Dict) -> go.layout.Template:
    """Create a Plotly template matching a LaTeX preset."""
    # Map preset font sizes, dimensions, and colors to Plotly template
    font_size_base = preset_info.get("font_size_base", 8)
    font_family = "serif" if preset_info.get("font_family", "serif") == "serif" else "Arial, sans-serif"

    return go.layout.Template(
        layout=go.Layout(
            colorway=WONG_PALETTE,
            font=dict(family=font_family, size=font_size_base),
            # ... map all preset properties
        ),
    )

def register_all_templates(presets: Dict[str, Dict]) -> None:
    """Register ring5_base + one template per preset."""
    pio.templates["ring5_base"] = create_base_template()
    for name, info in presets.items():
        pio.templates[f"ring5_{name}"] = create_preset_template(name, info)
```

Read presets from `latex_presets.yaml` via `PresetManager.list_presets()`.

**Tests**:
- `test_base_template_properties` — verify colorway, no top/right axis lines concept
- `test_preset_template_matches_yaml` — for each preset, verify font size/family match YAML
- `test_template_registration` — after `register_all_templates()`, `"ring5_isca" in pio.templates`
- `test_template_composition` — `"plotly_white+ring5_isca"` produces valid figure

**Commit**: `[Phase 1 / Step 12] Create PlotlyTemplateFactory with base + per-preset templates`

---

## Phase 1 Review Checkpoint

Before proceeding to Phase 2:
1. `./python_venv/bin/pytest tests/ -q -x --tb=short` — ALL green
2. `./python_venv/bin/mypy src/core/visualization/ --strict` — zero errors
3. `./python_venv/bin/black src/ tests/ -q` — formatted
4. `./python_venv/bin/flake8 src/core/visualization/ --max-line-length=120` — clean
5. Verify new test count: should be ~3,328 + ~150 = ~3,478

**PR-Level Review** (see Phase Review Protocol in ABSOLUTE RULES):
- Review EVERY file created/modified in Steps 4–12
- Verify all new dataclasses have complete type annotations, `__post_init__` validation, and docstrings
- Verify template factory does not leak Plotly internals to domain layer
- Check that all widget definitions have `spec_path` set
- Check test coverage on all new public APIs
- Ensure no `Any` leaked back into any spec file
- Write the PR-level summary with: overview of Phase 1 changes, risk areas, test adequacy assessment, and any technical debt introduced

**Commit**: `[Phase 1 / Review] PR-level review — Phase 1 complete`

---

## Phase 2: Unified Pipeline + Engine Toggle (Steps 13–22)

**Goal**: Replace dual-write `StyleApplicator` with spec-driven rendering, add engine toggle, unify presets, delete the export monolith.

### Step 13 — Rewire `StyleApplicator.apply_styles()`

**File**: `src/web/pages/ui/plotting/styles/applicator.py`

**Replace** all direct `fig.update_layout()` calls in `apply_styles()` with:
```python
def apply_styles(self, fig: go.Figure, config: Dict[str, Any], plot_type: str) -> None:
    from src.core.visualization.connectors.builders import ConfigSpecBuilder
    from src.core.visualization.resolvers import resolve_spec
    from src.core.visualization.connectors.plotly_connector import FigureSpecToPlotly

    spec = ConfigSpecBuilder.from_config(config, plot_type)
    spec = resolve_spec(spec)
    self.last_spec = spec
    FigureSpecToPlotly.apply(spec, fig)
```

The ~600 lines of private `_apply_*` methods become dead code. **Do NOT delete them yet** — that happens in Step 20.

**WARNING**: This is the riskiest step. After this change, run tests AND manually verify the plots look correct (if you can run Streamlit). If tests fail, the connector (Step 10) is missing features. Fix the connector, not the applicator.

**Tests**: Existing tests that exercise `StyleApplicator` should still pass. If they don't, it means the FigureSpec pipeline is missing something.

**Commit**: `[Phase 2 / Step 13] Rewire StyleApplicator to use FigureSpecToPlotly connector`

---

### Step 14 — Add engine state management

**Create**: `src/web/services/engine_manager.py`

```python
"""Engine state management for visualization rendering."""
from __future__ import annotations

from typing import Literal
import streamlit as st

EngineMode = Literal["plotly", "matplotlib"]

class EngineManager:
    """Manages the visualization engine state in Streamlit session."""

    STATE_KEY: str = "ring5_engine_mode"

    @staticmethod
    def get_engine() -> EngineMode:
        """Get current engine mode. Default: plotly."""
        return st.session_state.get(EngineManager.STATE_KEY, "plotly")

    @staticmethod
    def set_engine(mode: EngineMode) -> None:
        """Set engine mode and trigger rerun if changed."""
        current = EngineManager.get_engine()
        if current != mode:
            st.session_state[EngineManager.STATE_KEY] = mode

    @staticmethod
    def is_plotly() -> bool:
        return EngineManager.get_engine() == "plotly"

    @staticmethod
    def is_matplotlib() -> bool:
        return EngineManager.get_engine() == "matplotlib"
```

**Tests**: Mock `st.session_state` dict, verify get/set/toggle behavior.

**Commit**: `[Phase 2 / Step 14] Add EngineManager for engine state management`

---

### Step 15 — Add engine toggle widget

**File**: `src/web/pages/ui/plotting/plot_renderer.py`

Add engine toggle above the plot area. Find the place where the plot is rendered and add:

```python
from src.web.services.engine_manager import EngineManager

engine_choice = st.pills(
    "Engine",
    options=["plotly", "matplotlib"],
    format_func=lambda x: ":material/interactive_space: Plotly" if x == "plotly" else ":material/description: LaTeX (Matplotlib)",
    selection_mode="single",
    default="plotly",
    key=f"engine_selector_{plot_id}",
)
if engine_choice is not None:
    EngineManager.set_engine(engine_choice)
```

When engine changes, `st.rerun()` to re-render with the new engine.

**Tests**: UI logic test — mock `st.pills`, verify `EngineManager.set_engine()` is called.

**Commit**: `[Phase 2 / Step 15] Add engine toggle pills widget above plot area`

---

### Step 16 — Implement Matplotlib rendering path

**File**: `src/web/pages/ui/plotting/plot_renderer.py`

When `EngineManager.is_matplotlib()`:

1. Build `FigureSpec` from config (same pipeline as Plotly)
2. Create figure: `fig, ax = FigureSpecToMatplotlib.create_figure(spec)`
3. **Recreate data traces** on `ax`:
   - Dispatch by plot type (bar → `ax.bar()`, line → `ax.plot()`, scatter → `ax.scatter()`)
   - Create a `MatplotlibTraceRenderer` class or methods on each plot type
   - Use the plot's DataFrame + column mappings to draw
4. Apply styling: `FigureSpecToMatplotlib.apply(spec, ax)`
5. Render: `st.pyplot(fig, clear_figure=True)`
6. Store `fig` in session state for download

**This is complex.** The data rendering (step 3) needs to understand each plot type's data structure. Look at how the existing export pipeline (`matplotlib_converter.py`) recreates traces.

**Tests**: Integration test — create config + sample data → render in matplotlib mode → verify figure has axes, bars/lines.

**Commit**: `[Phase 2 / Step 16] Implement Matplotlib rendering path with trace recreation`

---

### Step 17 — Unify preset system

**Create**: `src/web/services/preset_applicator.py`

```python
"""Unified preset application across engines."""
from __future__ import annotations

from typing import Dict, Any
from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.connectors.builders import PresetSpecBuilder

class PresetApplicator:
    """Apply preset values onto FigureSpec, engine-agnostic."""

    @staticmethod
    def apply(preset_name: str, spec: FigureSpec, preset_info: Dict[str, Any]) -> FigureSpec:
        """Overlay preset values onto existing spec. Returns new spec."""
        preset_spec = PresetSpecBuilder.from_preset(preset_info)
        # Merge: preset values override spec values where set
        # Use dataclasses.replace() for immutable update
        # ...
        return merged_spec
```

For Plotly engine: also apply `fig.update_layout(template=f"ring5_{preset_name}")`.
For Matplotlib engine: also set rcParams context from preset.

Refactor `LaTeXPreset` into `UnifiedPreset` (or keep `LaTeXPreset` but make it engine-agnostic).

**Tests**: Apply ISCA preset → verify all font sizes, dimensions changed. Apply same preset to both engines → verify identical `FigureSpec`.

**Commit**: `[Phase 2 / Step 17] Create unified PresetApplicator for engine-agnostic preset application`

---

### Step 18 — Implement Plotly download (replaces export for Plotly engine)

When engine is Plotly, download uses **Kaleido v1**:

```python
# PNG
png_bytes = fig.to_image(format="png", width=w, height=h, scale=2)

# SVG
svg_bytes = fig.to_image(format="svg", width=w, height=h)

# PDF
pdf_bytes = fig.to_image(format="pdf", width=w, height=h)

# Show download button
st.download_button("📥 Download PNG", data=png_bytes, file_name="plot.png", mime="image/png")
```

Create a slim download section (can be a function or small class). Show format selector via `st.pills("Format", ["PNG", "SVG", "PDF"], selection_mode="single")`.

**Tests**: Verify `fig.to_image()` returns bytes with correct magic bytes (PNG header: `\x89PNG`, PDF header: `%PDF-`, SVG starts with `<svg` or `<?xml`).

**Commit**: `[Phase 2 / Step 18] Implement Plotly download path with Kaleido v1`

---

### Step 19 — Implement Matplotlib download

When engine is Matplotlib, download uses **savefig**:

```python
import io
from matplotlib.figure import Figure

def get_matplotlib_download(fig: Figure, format: str, dpi: int, spec: FigureSpec) -> bytes:
    buf = io.BytesIO()
    if format == "pgf":
        with plt.rc_context({
            "pgf.texsystem": "xelatex",
            "pgf.preamble": spec.latex_extra_preamble,
            "pgf.rcfonts": True,
        }):
            fig.savefig(buf, format="pgf", backend="pgf")
    elif format == "pdf":
        fig.savefig(buf, format="pdf", dpi=dpi, bbox_inches="tight")
    elif format == "png":
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    elif format == "svg":
        fig.savefig(buf, format="svg", bbox_inches="tight")
    buf.seek(0)
    return buf.read()
```

Show format pills: `st.pills("Format", ["PDF", "PGF", "PNG", "SVG"], selection_mode="single")`.

**Tests**: Verify savefig produces bytes. PGF output contains `\begin{pgfpicture}`. PDF starts with `%PDF-`. PNG has correct header.

**Commit**: `[Phase 2 / Step 19] Implement Matplotlib download path with PGF backend support`

---

### Step 20 — Delete `StyleApplicator` dead code

**File**: `src/web/pages/ui/plotting/styles/applicator.py`

Delete all private `_apply_*` methods (~600 lines) that became dead code in Step 13. The `apply_styles()` method should now be ~15 lines:

```python
def apply_styles(self, fig: go.Figure, config: Dict[str, Any], plot_type: str) -> None:
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    spec = resolve_spec(spec)
    self.last_spec = spec
    FigureSpecToPlotly.apply(spec, fig)
```

Consider whether `StyleApplicator` class is still needed or should be inlined into `PlotRenderer`.

**Tests**: Existing tests should still pass (they test the pipeline, not the private methods).

**Commit**: `[Phase 2 / Step 20] Delete StyleApplicator dead code (~600 lines)`

---

### Step 21 — Delete `_render_download_button` monolith

**File**: `src/web/pages/ui/plotting/plot_renderer.py`

Replace the ~987 line `_render_download_button()` method with a slim `_render_download_section()` that:
1. Checks current engine via `EngineManager`
2. For Plotly: calls the download function from Step 18
3. For Matplotlib: calls the download function from Step 19
4. Shows engine-appropriate format pills and download button

Target: ~50-80 lines replacing ~987 lines.

**Create**: `src/web/pages/ui/plotting/download_section.py` with the download logic, keeping `plot_renderer.py` thin.

**Tests**: Verify the download section renders for both engines. Verify format selection works.

**Commit**: `[Phase 2 / Step 21] Replace download monolith with slim download_section (~900 lines deleted)`

---

### Step 22 — Delete legacy export infrastructure

**Delete these files**:
- `src/web/pages/ui/plotting/export/converters/impl/layout_applier.py` (891 lines)
- `src/web/pages/ui/plotting/export/converters/impl/layout_mapper.py` (430 lines)
- `src/web/pages/ui/plotting/export/converters/impl/matplotlib_converter.py` (910 lines)
- `src/web/pages/ui/plotting/export/latex_export_service.py` (175 lines)

**Keep** the presets directory (`preset_manager.py`, `preset_schema.py`, `latex_presets.yaml`) — they're still needed for the unified preset system.

**Keep** `base_converter.py` only if it's used elsewhere. If not, delete it too.

Update all imports that referenced deleted files. If any remaining code imports from the deleted modules, refactor to use the new connector-based pipeline.

**Net deletion**: ~2,400 lines.

**Tests**: Remove or update tests that directly tested deleted classes. Ensure all remaining tests pass.

**Commit**: `[Phase 2 / Step 22] Delete legacy export infrastructure (~2,400 lines)`

---

## Phase 2 Review Checkpoint

Before proceeding to Phase 3:
1. `./python_venv/bin/pytest tests/ -q -x --tb=short` — ALL green
2. `./python_venv/bin/mypy src/core/visualization/ --strict` — zero errors
3. `./python_venv/bin/mypy src/web/services/ --strict` — zero errors
4. `./python_venv/bin/black src/ tests/ -q` — formatted
5. `./python_venv/bin/flake8 src/ --max-line-length=120` — no new violations
6. Verify test count: should still be ~3,400+ (some old tests removed, new ones added)
7. **Manual verification (if possible)**: Run `./python_venv/bin/streamlit run app.py`, create a grouped bar plot, toggle engine, verify both render correctly, test download in both engines.

**PR-Level Review** (see Phase Review Protocol in ABSOLUTE RULES):
- Review EVERY file modified in Steps 13–22
- This phase has the HIGHEST RISK — it rewires the rendering pipeline and deletes ~2,400 lines
- Verify `StyleApplicator.apply_styles()` is now a thin dispatcher (< 30 lines), not a monolith
- Verify ALL export converter files are truly deleted and no orphan imports remain
- Verify engine toggle works correctly via `EngineManager` — no direct session state manipulation
- Verify download section is self-contained, slim, and does NOT duplicate rendering logic
- Verify NO threading or concurrent code was introduced
- Run `grep -r "import threading\|from threading\|concurrent.futures\|multiprocessing" src/` to confirm
- Write the PR-level summary with: overview of Phase 2 changes, deletion inventory, risk areas, regression analysis, test adequacy

**Commit**: `[Phase 2 / Review] PR-level review — Phase 2 complete`

---

## Phase 3: Pills UI Reorganization (Steps 23–31)

**Goal**: Replace the two-expander layout ("⚙️ Advanced Options" + "🎨 Theme & Style") with pills-driven sidebar sections.

### Step 23 — Design pills navigation hierarchy

This is a design step — create the data structure that drives navigation:

**Create**: `src/web/pages/ui/plotting/settings_pills.py`

```python
"""Pills-driven settings navigation for plot styling."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Callable, Optional
import streamlit as st

@dataclass(frozen=True)
class SettingsSection:
    """A settings section accessible via pills navigation."""
    key: str
    label: str
    icon: str  # Material icon name
    advanced: bool = False  # Hidden by default in progressive disclosure

# Top-level navigation sections
SETTINGS_SECTIONS: List[SettingsSection] = [
    SettingsSection("layout", "Layout", "dashboard"),
    SettingsSection("typography", "Typography", "text_fields"),
    SettingsSection("legends", "Legends", "legend_toggle"),
    SettingsSection("axes", "Axes", "straighten", advanced=True),
    SettingsSection("data_labels", "Data Labels", "label", advanced=True),
    SettingsSection("colors", "Colors", "palette", advanced=True),
    SettingsSection("advanced", "Advanced", "tune", advanced=True),
]

def render_settings_pills(show_advanced: bool = False) -> Optional[str]:
    """Render the top-level pills navigation. Returns selected section key."""
    visible = [s for s in SETTINGS_SECTIONS if not s.advanced or show_advanced]
    options = [s.key for s in visible]
    labels = {s.key: f":material/{s.icon}: {s.label}" for s in visible}

    selected = st.pills(
        "Settings",
        options=options,
        format_func=lambda x: labels[x],
        selection_mode="single",
        key="settings_nav",
    )
    return selected
```

**Tests**: Unit test `SettingsSection` dataclass, test `SETTINGS_SECTIONS` has expected entries, test progressive disclosure filtering.

**Commit**: `[Phase 3 / Step 23] Design pills navigation hierarchy with SettingsSection dataclass`

---

### Step 24 — Implement top-level pills navigation

**File**: `src/web/pages/ui/plotting/styles/base_ui.py` (or wherever the sidebar styling expanders currently live)

Find the two `st.expander` blocks:
- "⚙️ Advanced Options" (~L358 in `plot_manager_components.py`)
- "🎨 Theme & Style" (~L363)

Replace both with:
```python
from src.web.pages.ui.plotting.settings_pills import render_settings_pills

show_advanced = st.toggle("Show advanced settings", value=False, key=f"show_advanced_{plot_id}")
selected_section = render_settings_pills(show_advanced=show_advanced)

if selected_section == "layout":
    render_layout_section(config, plot_id)
elif selected_section == "typography":
    render_typography_section(config, plot_id)
elif selected_section == "legends":
    render_legends_section(config, plot_id)
# ... etc.
```

Each section renderer uses `WidgetRenderer.render_section()` for its `WidgetSection`s.

**WARNING**: This changes the UI structure significantly. Existing widget keys must be preserved to maintain session state compatibility. Use the same `key=` values for all widgets.

**Tests**: UI logic test — mock `st.pills` and `st.toggle`, verify correct section renderer is called.

**Commit**: `[Phase 3 / Step 24] Implement top-level pills navigation replacing expanders`

---

### Step 25 — Implement Legend sub-pills

When "Legends" pill is selected, show sub-pills:

```python
def render_legends_section(config: Dict[str, Any], plot_id: str) -> None:
    legend_tab = st.pills(
        "Legend",
        options=["primary", "secondary", "boxed"],
        format_func=lambda x: {"primary": "Primary", "secondary": "Secondary (Legend 2)", "boxed": "Boxed (Legend 3)"}[x],
        selection_mode="single",
        key=f"legend_nav_{plot_id}",
        default="primary",
    )

    # Determine key prefix based on selection
    prefix_map = {"primary": "legend_", "secondary": "legend2_", "boxed": "legend3_"}
    prefix = prefix_map.get(legend_tab, "legend_")

    # Render same widget schema with different key prefixes
    WidgetRenderer.render_section(LEGEND_POSITION, config, key_prefix=prefix)
    WidgetRenderer.render_section(LEGEND_APPEARANCE, config, key_prefix=prefix)
    WidgetRenderer.render_section(LEGEND_SIZING, config, key_prefix=prefix)
```

This maps to `FigureSpec.legends[0]`, `[1]`, `[2]` respectively.

**Tests**: Verify each sub-pill renders the correct prefix, verify config keys have correct prefixes.

**Commit**: `[Phase 3 / Step 25] Implement Legend sub-pills for primary/secondary/boxed legends`

---

### Step 26 — Implement Axes sub-pills

When "Axes" pill is selected:

```python
def render_axes_section(config: Dict[str, Any], plot_id: str) -> None:
    axis_tab = st.pills(
        "Axis",
        options=["x", "y_left", "y_right"],
        format_func=lambda x: {"x": "X-Axis", "y_left": "Y-Left", "y_right": "Y-Right"}[x],
        selection_mode="single",
        key=f"axis_nav_{plot_id}",
        default="x",
    )

    # Each renders: label, font size, tick font/angle/color, range, scale, dtick, grid, axis line color
    if axis_tab == "x":
        render_x_axis_widgets(config, plot_id)
    elif axis_tab == "y_left":
        render_y_axis_widgets(config, plot_id)
    elif axis_tab == "y_right":
        render_y2_axis_widgets(config, plot_id)
```

Map to `FigureSpec.axes.xaxis`, `.yaxis`, `.y2axis`.

**Tests**: Verify correct axis widgets rendered per sub-pill selection.

**Commit**: `[Phase 3 / Step 26] Implement Axes sub-pills for X/Y-Left/Y-Right`

---

### Step 27 — Create new `WidgetSection` definitions

**File**: `src/core/visualization/widgets/widget_def.py`

Add missing sections:

```python
COLORS_PALETTE = WidgetSection(
    name="Colors & Palette",
    widgets=[
        # Palette selector, hatching toggle, stripe toggle, contrast mode
    ],
)

REFERENCE_LINES = WidgetSection(
    name="Reference Lines",
    widgets=[
        # Add/remove lines with axis, value, color, style
    ],
)

AXIS_X = WidgetSection(name="X-Axis", widgets=[...])  # Split from combined axis config
AXIS_Y = WidgetSection(name="Y-Axis", widgets=[...])
AXIS_Y2 = WidgetSection(name="Y2-Axis", widgets=[...])

ADVANCED = WidgetSection(
    name="Advanced",
    widgets=[
        # Hovermode, error bars, separator config
    ],
)
```

**Tests**: Verify each section has expected widget count and types.

**Commit**: `[Phase 3 / Step 27] Create new WidgetSection definitions for pills navigation`

---

### Step 28 — Wire `spec_path` on ALL `WidgetDef` instances

**File**: `src/core/visualization/widgets/widget_def.py`

Currently only 18 of ~50 widgets have `spec_path`. Complete the mapping for ALL:

| Widget Key | `spec_path` |
|-----------|-------------|
| `width` | `dimensions.width` |
| `height` | `dimensions.height` |
| `automargin` | `axes.xaxis.automargin` |
| `xaxis_tickangle` | `axes.xaxis.tick_angle` |
| `legend_orientation` | `legends.0.orientation` |
| `legend_x` | `legends.0.x` |
| `legend_y` | `legends.0.y` |
| `legend_xanchor` | `legends.0.xanchor` |
| `legend_yanchor` | `legends.0.yanchor` |
| `show_values` | `data_labels.enabled` |
| `text_font_size` | `data_labels.font_size` |
| `axis_color` | `axes.xaxis.axis_line_color` |
| `grid_color` | `axes.xaxis.tick_font_color` |
| `title` | `title` |
| `xlabel` | `axes.xaxis.label` |
| `ylabel` | `axes.yaxis.label` |
| ... (complete all remaining) |

This enables `ConfigBridge` to do full bidirectional FigureSpec ↔ config translation, which is critical for portfolio save/load.

**Tests**: For each widget with `spec_path`, verify `ConfigBridge.config_to_spec()` and `ConfigBridge.spec_to_config()` roundtrip correctly.

**Commit**: `[Phase 3 / Step 28] Wire spec_path on all WidgetDef instances for full bidirectional bridge`

---

### Step 29 — Add preset selector to sidebar

Add above the pills navigation:

```python
from src.web.services.preset_applicator import PresetApplicator

preset = st.pills(
    "Preset",
    options=["none", "isca", "micro", "asplos", "hpca", "nature", "science", "poster", "slides"],
    format_func=lambda x: "None" if x == "none" else x.upper(),
    selection_mode="single",
    key=f"preset_selector_{plot_id}",
    default="none",
)
if preset and preset != "none":
    # Apply preset to current FigureSpec
    preset_info = PresetManager.get_preset_info(preset)
    spec = PresetApplicator.apply(preset, spec, preset_info)
    # Update config from spec for widget display
    config = ConfigBridge.spec_to_config(spec)
```

**Tests**: Verify preset selection updates config values. Verify "none" clears preset overrides.

**Commit**: `[Phase 3 / Step 29] Add preset selector pills to sidebar`

---

### Step 30 — Add engine-specific controls

Below the pills, show conditional sections:

**Plotly mode**:
- Hovermode selector (x unified, closest, off)
- Zoom config toggle
- Legend drag toggle

**Matplotlib mode**:
- LaTeX preamble text input (`spec.latex_extra_preamble`)
- TeX system choice (xelatex / pdflatex / lualatex)
- PGF vs PDF backend radio

```python
if EngineManager.is_plotly():
    with st.expander(":material/interactive_space: Interactive Settings"):
        hovermode = st.selectbox("Hover mode", ["x unified", "closest", False], key=...)
elif EngineManager.is_matplotlib():
    with st.expander(":material/description: LaTeX Settings"):
        preamble = st.text_area("Extra LaTeX preamble", key=...)
        tex_system = st.selectbox("TeX system", ["xelatex", "pdflatex", "lualatex"], key=...)
```

**Tests**: Verify only relevant controls shown per engine.

**Commit**: `[Phase 3 / Step 30] Add engine-specific controls for Plotly interactive and LaTeX settings`

---

### Step 31 — Progressive disclosure

Default view shows only **Layout + Typography + Legends** pills. An advanced toggle reveals the rest:

```python
show_advanced = st.toggle(
    "Show advanced settings",
    value=False,
    key=f"show_advanced_{plot_id}",
    help="Show Axes, Data Labels, Colors, and Advanced sections",
)
```

This follows "less is more" from data visualization literature — don't overwhelm with 50+ controls on first view.

**Tests**: Verify only 3 pills visible when advanced=False, all 7 when True.

**Commit**: `[Phase 3 / Step 31] Implement progressive disclosure for settings pills`

---

## Phase 3 Review Checkpoint

1. Full test suite green
2. mypy strict on `src/core/visualization/` and `src/web/services/`
3. Black + flake8 clean
4. Manual verification: pills UI works, sections render, sub-pills for legends/axes work

**PR-Level Review** (see Phase Review Protocol in ABSOLUTE RULES):
- Review EVERY file created/modified in Steps 23–31
- Verify `st.pills` usage is correct and follows Streamlit 1.53+ API
- Verify progressive disclosure logic is clean — no complex nested conditionals
- Verify Material icon names are valid and render correctly
- Check that pills navigation state is properly managed in session state
- Verify no business logic leaked into UI components (pills should only route, not compute)
- Ensure all UI components have clear docstrings and type hints
- Write the PR-level summary with: overview of UI changes, usability assessment, state management review, test coverage

**Commit**: `[Phase 3 / Review] PR-level review — Phase 3 complete`

---

## Phase 4: Portfolio Compatibility & Migration (Steps 32–34)

**Goal**: Ensure saved portfolios work after config key changes.

### Step 32 — Create `PortfolioMigrator`

**Create**: `src/web/services/portfolio_migrator.py`

```python
"""Portfolio schema migration for backward compatibility."""
from __future__ import annotations

from typing import Any, Dict, List

class PortfolioMigrator:
    """Migrate portfolio JSON between schema versions."""

    CURRENT_VERSION: int = 2

    @staticmethod
    def migrate(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate portfolio to current schema version."""
        version = portfolio_data.get("schema_version", 1)

        if version < 2:
            portfolio_data = PortfolioMigrator._migrate_v1_to_v2(portfolio_data)

        portfolio_data["schema_version"] = PortfolioMigrator.CURRENT_VERSION
        return portfolio_data

    @staticmethod
    def _migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
        """V1→V2: Add engine field, clean export keys."""
        for plot in data.get("plots", []):
            config = plot.get("config", {})
            # Add engine default
            config.setdefault("engine", "plotly")
            # Remove deprecated export_* keys (handled by download section now)
            keys_to_remove = [k for k in config if k.startswith("export_")]
            for k in keys_to_remove:
                del config[k]
            # Preserve unknown keys for forward compatibility
        return data
```

**Tests**:
- `test_v1_migration` — V1 portfolio gets engine field, export keys removed
- `test_unknown_keys_preserved` — custom keys survive migration
- `test_already_v2_no_change` — idempotent

**Commit**: `[Phase 4 / Step 32] Create PortfolioMigrator for backward-compatible schema migration`

---

### Step 33 — Add portfolio save/load through `FigureSpec`

**Modify**: `src/core/services/data_services/portfolio_service.py`

Instead of saving raw flat config dict, save `FigureSpec.to_dict()` alongside:

```python
plot_data = {
    "config": plot.config,              # Keep for backward compat
    "figure_spec": spec.to_dict(),      # New canonical representation
    "engine": EngineManager.get_engine(),
}
```

On load:
```python
if "figure_spec" in plot_data:
    spec = FigureSpec.from_dict(plot_data["figure_spec"])
    config = ConfigBridge.spec_to_config(spec)
else:
    # Legacy portfolio — use raw config
    config = plot_data["config"]
```

**Tests**: Save portfolio → load → verify identical FigureSpec. Load legacy (no figure_spec) → verify config works.

**Commit**: `[Phase 4 / Step 33] Add FigureSpec-based portfolio save/load`

---

### Step 34 — Migration integration test

**Create**: `tests/integration/test_portfolio_migration.py`

Test with sample portfolio JSON fixtures:
- Load V1 portfolio → migrate → verify valid FigureSpec
- Load V2 portfolio → no migration needed → verify passes through
- Render migrated portfolio in both engines without errors
- Verify roundtrip: load → save → load → identical

**Commit**: `[Phase 4 / Step 34] Portfolio migration integration tests`

---

## Phase 4 Review Checkpoint

1. Full test suite green
2. mypy strict clean
3. Portfolio save/load works with migration

**PR-Level Review** (see Phase Review Protocol in ABSOLUTE RULES):
- Review EVERY file created/modified in Steps 32–34
- Verify `PortfolioMigrator` handles ALL config key changes from Phases 1–3
- Verify migration is idempotent (migrating an already-migrated portfolio is a no-op)
- Verify backward compatibility — old portfolio files still load correctly
- Check error handling for corrupted/malformed portfolio files
- Write the PR-level summary with: migration coverage, backward compatibility analysis, edge cases tested

**Commit**: `[Phase 4 / Review] PR-level review — Phase 4 complete`

---

## Phase 5: Polish, Accessibility & Documentation (Steps 35–38)

### Step 35 — Colorblind-safe defaults

**File**: `src/core/visualization/figure_spec.py`

Set default `color_palette` to Wong palette (already done in Step 6). Add:

**File**: `src/web/pages/ui/plotting/settings_pills.py` (Colors section)

- Palette preview widget showing color swatches
- Built-in palette selector: Wong, Viridis, Plasma, seaborn-colorblind, custom
- Contrast mode toggle

```python
BUILTIN_PALETTES = {
    "wong": ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"],
    "viridis_8": ["#440154", "#482878", "#3E4A89", "#31688E", "#26838E", "#1F9E89", "#6DCD59", "#FDE725"],
    "seaborn_cb": ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494"],
}
```

**Tests**: Verify default palette is Wong. Verify palette selector updates `color_palette` config key.

**Commit**: `[Phase 5 / Step 35] Colorblind-safe palette defaults and palette selector`

---

### Step 36 — Publication quality validation

**Create**: `src/core/visualization/publication_validator.py`

```python
"""Validate FigureSpec for publication quality."""
from __future__ import annotations

from typing import List
from src.core.visualization.figure_spec import FigureSpec

VENUE_REQUIREMENTS = {
    "isca": {"min_font": 7, "min_dpi": 300, "max_width": 3.5, "max_height": 5.0},
    "nature": {"min_font": 6, "min_dpi": 600, "max_width": 3.5, "max_height": 10.0},
    # ... etc
}

def validate_for_publication(spec: FigureSpec, target: str) -> List[str]:
    """Check spec against venue requirements. Returns list of warnings."""
    warnings: List[str] = []
    reqs = VENUE_REQUIREMENTS.get(target, {})

    min_font = reqs.get("min_font", 7)
    if spec.typography and spec.typography.font_size_ticks > 0:
        if spec.typography.font_size_ticks < min_font:
            warnings.append(f"Tick font size ({spec.typography.font_size_ticks}pt) below {target} minimum ({min_font}pt)")

    min_dpi = reqs.get("min_dpi", 300)
    if spec.dimensions.dpi < min_dpi:
        warnings.append(f"DPI ({spec.dimensions.dpi}) below {target} minimum ({min_dpi})")

    # Check dimensions, color palette, etc.
    return warnings
```

Show warnings as `st.warning()` in the download section.

**Tests**: Verify warnings raised for undersized fonts, low DPI, oversized figures.

**Commit**: `[Phase 5 / Step 36] Add publication quality validator with venue-specific checks`

---

### Step 37 — Rename "Export" → "Download" in all UI strings

**Global search and replace**:
- "Export for LaTeX" → "Download"
- "Export Settings" → removed (settings are inline)
- "Export" → "Download" (in button labels, headers, tooltips)
- Keep internal class/module names that still make architectural sense

```bash
# Find all occurrences
grep -rn "Export\|export" src/web/ --include="*.py" | grep -v "import\|__pycache__\|\.pyc"
```

Replace UI-facing strings only. Internal variable names like `export_format` can stay if they're clear.

**Tests**: Verify no UI-facing string contains "Export" (can add a principle compliance test).

**Commit**: `[Phase 5 / Step 37] Rename all UI strings from "Export" to "Download"`

---

### Step 38 — Update documentation

**Files**:
- `docs/LaTeX-Export-Guide.md` → Rename to `docs/Download-Guide.md`. Rewrite with engine comparison table (Plotly formats vs Matplotlib formats).
- `docs/Creating-Plots.md` → Update with pills UI description (no screenshots needed, describe the navigation).
- `docs/Architecture.md` → Add/update pipeline diagram showing FigureSpec → Engine dispatch → Connector → Render.
- `CONTRIBUTING.md` → Add section on the new testing patterns (connector tests, spec roundtrip tests).

**Commit**: `[Phase 5 / Step 38] Update documentation for new architecture and UI`

---

## Final Review Checkpoint — CRITICAL (Main Branch Merge)

> ⚠️ **These changes will be merged into the MAIN branch.** This review must be exhaustive, rigorous, and leave ZERO doubt about quality. Treat this as a production release gate.

After ALL steps are complete:

### 1. Automated Validation

1. **Full test suite**: `./python_venv/bin/pytest tests/ -q --tb=short` — ALL green, zero failures, zero warnings
2. **Type checking (ENTIRE src/)**: `./python_venv/bin/mypy src/ --strict` — zero errors across the ENTIRE source tree
3. **Formatting**: `./python_venv/bin/black src/ tests/ --check` — already formatted (no changes needed)
4. **Linting**: `./python_venv/bin/flake8 src/ tests/ --max-line-length=120` — clean
5. **Test count**: Baseline 3,328 + ~290 new = ~3,618 minimum
6. **No threading verification**: `grep -rn "import threading\|from threading\|concurrent.futures\|from multiprocessing" src/core/visualization/ src/web/pages/ui/plotting/` — zero matches in new/modified code

### 2. Deep Architecture Review

Go through EVERY file touched during this plan — not just spot checks. Verify:

- [ ] No `Any` types in `FigureSpec` or any spec dataclass
- [ ] No direct `fig.update_layout()` outside connectors
- [ ] No `st.expander` for styling (all pills-driven)
- [ ] No "Export" in UI strings — terminology is "Download"
- [ ] All private `_apply_*` methods in StyleApplicator deleted
- [ ] All export converter files deleted (layout_applier, layout_mapper, matplotlib_converter, latex_export_service)
- [ ] `interactive_plotly_chart` unchanged (diff against base commit)
- [ ] `layout='constrained'` in matplotlib `create_figure()`
- [ ] `plt.close(fig)` after every matplotlib render — no figure leaks
- [ ] Wong palette as default colorway
- [ ] Layer A/B never import Streamlit
- [ ] All new public functions/methods have docstrings
- [ ] All new modules have module-level docstrings
- [ ] No magic numbers — all constants are named
- [ ] No commented-out code
- [ ] No TODO/FIXME/HACK comments left unresolved
- [ ] Import ordering is consistent (stdlib → third-party → local)

### 3. Performance & Memory Review

- [ ] No O(n²) patterns in rendering or template composition
- [ ] No unbounded caches or growing lists
- [ ] All matplotlib figures are explicitly closed after use
- [ ] No large objects stored in module-level globals
- [ ] Fixtures are function-scoped by default
- [ ] Test data is minimal — no loading full gem5 outputs when a 10-row fixture suffices

### 4. Comprehensive Diff Review

Run `git diff 0c2c56d..HEAD --stat` and `git diff 0c2c56d..HEAD` to review EVERY change:

- Read through the entire diff methodically
- Flag any inconsistencies, dead code, or incomplete implementations
- Verify deletion count matches expectations (~3,800 lines removed)
- Verify addition count matches expectations (~2,000 lines added)
- Confirm net reduction is ~1,800 lines

### 5. Regression Analysis

- [ ] Run specific test suites for each area: parsing, plotting, UI, portfolio, export
- [ ] Verify no existing functionality is broken
- [ ] Test edge cases: empty data, single data point, very large datasets (if fixtures exist)
- [ ] Verify all presets still work with the new template system

### 6. Security & Robustness

- [ ] No `eval()` or `exec()` calls
- [ ] No hardcoded file paths (all relative or configurable)
- [ ] Proper error messages — no stack traces leak to UI
- [ ] Input validation on all public APIs

### 7. Net Code Change Verification

- ~+2,000 lines new (specs, connectors, UI, tests)
- ~−3,800 lines deleted (export monolith, layout_applier, layout_mapper, matplotlib_converter, StyleApplicator internals)
- Net: ~−1,800 lines (simpler, not more complex)

### 8. Final Verdict

Write a comprehensive **Final Review Report** containing:
- **Executive summary**: What was accomplished across all 5 phases
- **Architecture changes**: New patterns introduced, old patterns removed
- **Risk assessment**: Any areas of concern, technical debt, known limitations
- **Test coverage analysis**: New test count, coverage of new code, edge cases
- **Performance impact**: Expected impact on rendering speed, memory usage
- **Recommendation**: PASS (ready for main) or FAIL (with specific items to fix)

**This review must result in a PASS before the final commit.**

**Commit**: `[Final] Deep review passed — ready for main branch merge`

---

## Step 39 — Update Architecture Documentation

After the final review passes, update `.agent/ARCHITECTURE.md` to reflect ALL architectural changes made during this plan:

1. **Read the current architecture doc** to understand its structure and content
2. **Document new modules**: FigureSpec enhancements, DataLabelSpec, SeriesStyleSpec, PlotlyTemplateFactory, EngineManager, PresetApplicator, PortfolioMigrator, download_section, settings_pills
3. **Document deleted modules**: layout_applier, layout_mapper, matplotlib_converter, latex_export_service, StyleApplicator internals
4. **Document new patterns**: Spec-driven rendering pipeline, Plotly template composition, engine toggle architecture, pills-based navigation
5. **Document changed data flow**: How a plot goes from FigureSpec → connector → rendered figure → download
6. **Update layer descriptions**: Reflect that Layer C now uses pills instead of expanders, that export is now "download", that connectors handle ALL engine-specific logic
7. **Update file inventory**: Reflect the new file structure after creations and deletions

**Commit**: `[Post-Plan] Update ARCHITECTURE.md with all architectural changes`

---

## Key Decisions Reference

| Decision | Choice | Rationale |
|:---------|:-------|:----------|
| Plotly theming | Templates over manual `update_layout` | Idiomatic Plotly; composable; per-figure overridable |
| LaTeX export | PGF backend over PDF backend | PGF produces native LaTeX commands; fonts match document |
| Matplotlib layout | `layout='constrained'` over `tight_layout` | More robust for complex layouts; Matplotlib 3.x recommended |
| Static Plotly export | Kaleido v1 over Orca | Current recommended engine; uses system Chrome |
| Default palette | Wong 8-color over Viridis | Optimized for discrete categories; Viridis for continuous |
| Navigation | `st.pills` over `st.tabs` | User preference; more compact; Material icons |
| Portfolio format | FigureSpec-based over raw config | Future-proof; engine-agnostic by design |
| UI complexity | Progressive disclosure (3→7 pills) | "Less is more"; don't overwhelm with 50+ controls |

---

## File Impact Summary

### Files to CREATE (~2,000 lines)
| File | Purpose |
|------|---------|
| `src/core/visualization/data_label_spec.py` | DataLabelSpec dataclass |
| `src/core/visualization/series_style_spec.py` | SeriesStyleSpec dataclass |
| `src/core/visualization/connectors/plotly_templates.py` | PlotlyTemplateFactory |
| `src/core/visualization/publication_validator.py` | Publication quality checks |
| `src/web/services/engine_manager.py` | Engine state management |
| `src/web/services/preset_applicator.py` | Unified preset application |
| `src/web/services/portfolio_migrator.py` | Portfolio schema migration |
| `src/web/pages/ui/plotting/download_section.py` | Slim download UI |
| `src/web/pages/ui/plotting/settings_pills.py` | Pills navigation + routing |
| `.agent/context/visualization-best-practices.md` | Knowledge reference |
| ~15 test files | ~290 new test functions |

### Files to HEAVILY MODIFY
| File | Change |
|------|--------|
| `src/core/visualization/figure_spec.py` | Fix `Any`, add ~6 fields |
| `src/core/visualization/axis_spec.py` | Add 5 fields |
| `src/core/visualization/legend_spec.py` | Add 3 fields |
| `src/core/visualization/connectors/plotly_connector.py` | Add ~16 methods |
| `src/core/visualization/connectors/matplotlib_connector.py` | Add ~12 methods |
| `src/core/visualization/connectors/builders.py` | Map ~30 keys |
| `src/core/visualization/widgets/widget_def.py` | New sections + spec_path |
| `src/web/pages/ui/plotting/plot_renderer.py` | Engine toggle + download |
| `src/web/pages/ui/plotting/styles/applicator.py` | Collapse to ~15 lines |
| `.agent/rules/001-architecture-standards.md` | Add §9 |
| `.agent/rules/002-data-science-mastery.md` | Expand §4 |

### Files to DELETE (~3,800 lines)
| File | Lines |
|------|-------|
| `src/web/pages/ui/plotting/export/converters/impl/layout_applier.py` | 891 |
| `src/web/pages/ui/plotting/export/converters/impl/layout_mapper.py` | 430 |
| `src/web/pages/ui/plotting/export/converters/impl/matplotlib_converter.py` | 910 |
| `src/web/pages/ui/plotting/export/latex_export_service.py` | 175 |
| StyleApplicator `_apply_*` methods (dead code) | ~600 |
| `_render_download_button` monolith | ~987 |
