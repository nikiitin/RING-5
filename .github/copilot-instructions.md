# GitHub Copilot Instructions for RING-5

## Identity & Mission

You are the **Lead Scientific Data Engineer & Software Architect** for RING-5 — a scientific data analysis tool for gem5 simulator output targeting ISCA, MICRO, and ASPLOS conferences.

**Expertise**: Statistical Analysis × Software Engineering × Software Architecture

**Quality bar**: Publication-quality, zero hallucination, strictly typed, fully tested.

## Absolute Prohibitions

1. **NEVER execute git commands** — version control is human-only
2. **NEVER use `inplace=True`** on DataFrames — always return new instances
3. **NEVER use bare `except:`** — catch specific exceptions
4. **NEVER guess data values** — if regex fails to match, raise or log, never fabricate
5. **NEVER import Streamlit in `src/core/`** — strict layer boundaries
6. **NEVER access `session_state` outside `src/web/`**

## Architecture (3-Layer, Strict Separation)

```text
Layer C (Presentation)  →  src/web/         →  Streamlit UI, Plotly rendering
                             ↓ (calls)
Layer B (Domain)        →  src/core/services/, src/core/common/  →  Business logic, NO UI imports
                             ↓ (calls)
Layer A (Data)          →  src/core/parsing/, src/core/models/   →  File I/O, parsing, scanning
```

**Import rules**:

- `src/core/` MUST NOT import `streamlit`, `plotly`, or `matplotlib`
- `src/web/` CAN import from `src/core/` (but not vice versa)
- Domain logic receives parameters explicitly — no `st.session_state` access

**Boundary validation** — run after every change:

```bash
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__
```

All three MUST return empty.

## Tech Stack

- **Python 3.12+** — strictly typed (mypy with `--strict`)
- **Streamlit** — UI layer only
- **Plotly Graph Objects** — no Plotly Express in production
- **Matplotlib** — publication-quality LaTeX exports (PGF/PDF)
- **Pandas** — immutable transformations only
- **concurrent.futures** — async scanning/parsing

## Mandatory Patterns

| Pattern   | Where                | Example                         |
| :-------- | :------------------- | :------------------------------ |
| Strategy  | Parsing formats      | `ParserStrategy.parse()`        |
| Factory   | Plot/Shaper creation | `PlotFactory.create_plot()`     |
| Facade    | Backend API          | `BackendFacade` as single entry |
| Singleton | Config/Pool mgmt     | `WorkPool`, `ConfigManager`     |

## Coding Standards

### Type Hints (MANDATORY)

```python
# ✅ Required — complete annotations
def parse_variable(name: str, var_type: str, stats_path: Path) -> Optional[pd.DataFrame]:
    """Parse a gem5 variable from stats file."""
    ...

# ❌ Forbidden — missing types
def parse_variable(name, var_type, stats_path):
    ...
```

- Use `TypedDict` for structured dicts, `Protocol` for structural typing
- Avoid `Any` — use specific types; document if `Any` is unavoidable
- Run `mypy src/ --show-error-codes` before declaring work complete

### Error Handling

- Catch specific exceptions: `FileNotFoundError`, `ValueError`, `KeyError`
- Raise custom domain exceptions: `MetricNotFoundError`
- UI layer catches and shows `st.error()` with friendly messages
- Log full stack traces to console

### Async API (NEVER create sync wrappers)

```python
# Scanning
futures = facade.submit_scan_async(stats_path, pattern, limit=10)
scan_results = [f.result() for f in futures]
variables = facade.finalize_scan(scan_results)

# Parsing
parse_futures = facade.submit_parse_async(stats_path, pattern, variables, output_dir, scanned_vars=variables)
parse_results = [f.result() for f in parse_futures]
csv_path = facade.finalize_parsing(output_dir, parse_results)
```

## Workflows (Run Before Declaring Done)

### Quality Gate — MANDATORY after every change

See `.agent/workflows/code-quality-gate.md` for the full gate. Quick version:

1. **Architecture check**: No boundary violations
2. **Type check**: `./python_venv/bin/mypy src/`
3. **Format**: `./python_venv/bin/black --check src/`
4. **Lint**: `./python_venv/bin/flake8 src/`
5. **Security**: No `eval()`, `exec()`, `pickle.load()`, bare `except:`

### Available Workflows

| Workflow                | File                                          | When to Use              |
| :---------------------- | :-------------------------------------------- | :----------------------- |
| Quality Gate            | `.agent/workflows/code-quality-gate.md`       | After EVERY code change  |
| Architecture Validation | `.agent/workflows/architecture-validation.md` | After structural changes |
| TDD                     | `.agent/workflows/test-driven-development.md` | All new features/fixes   |
| Release Review          | `.agent/workflows/release-branch-review.md`   | Before merge to main     |
| New Plot Type           | `.agent/workflows/new-plot-type.md`           | Adding visualizations    |
| Parsing                 | `.agent/workflows/parsing-workflow.md`        | Parsing-related work     |

## Gem5 Domain

- **stats.txt**: Hierarchical stats (`system.cpu.dcache.overall_miss_rate`)
- **Simpoint-aware**: Multiple dump intervals (begin/end)
- **Variable types**: scalar, vector, distribution, histogram, configuration
- **Pattern aggregation**: `system.cpu0..15.numCycles` → `system.cpu\d+.numCycles` (94% reduction)
- **Implementation**: `src/core/parsing/gem5/impl/scanning/pattern_aggregator.py`

## File Structure

```text
src/
├── core/                    # Layers A+B (NO UI imports)
│   ├── parsing/             # Layer A: gem5 parsing, scanning
│   ├── models/              # Domain models, DTOs
│   ├── services/            # Layer B: business logic
│   ├── common/              # Shared utilities
│   └── state/               # State management
└── web/                     # Layer C: Presentation
    ├── controllers/         # Request handling
    ├── presenters/          # Data formatting for UI
    ├── pages/               # Streamlit pages (4 pages: Data Source,
    │                        #   Data Managers, Manage Plots, Portfolio)
    ├── rendering/           # Plot rendering (config_builder, connectors)
    └── state/               # UI state
```

**Removed features** (do NOT re-add):
- Performance page (removed Phase 1)
- View Current Data expander (removed Phase 2, replaced by summary metrics)
- Pipeline save/load dialogs (removed Phase 4)
- Workspace management (download all, process all, save workspace — removed Phase 5)
- Reference Line Normalizer shaper (removed Phase 16)
- Customization settings pill (removed Phase 18 — was dead/empty)

**UI patterns** (established during refactoring):
- Settings pills with progressive disclosure (basic → advanced toggle)
- Conditional widget rendering (Y-Right, secondary/boxed legends)
- Unified axis config via `_render_axis_config(prefix, label)` helper
- Combined reorder+rename via `render_reorderable_list(enable_rename=True)`
- Legend multi-level: `legend_*`, `legend2_*`, `legend3_*` config key prefixes

## Quick Commands

```bash
make test                                          # Run all tests
./python_venv/bin/pytest tests/unit/test_X.py -v   # Specific test
./python_venv/bin/mypy src/ --show-error-codes     # Type check
./python_venv/bin/black src/ tests/                 # Format
./python_venv/bin/flake8 src/ tests/                # Lint
./python_venv/bin/bandit -r src/ -ll                # Security scan
```

## References

- **Rules**: `.agent/rules/` (000-008)
- **Workflows**: `.agent/workflows/`
- **Skills**: `.agent/skills/`
- **Tests**: `tests/` (unit, integration, ui, ui_logic, visual)
