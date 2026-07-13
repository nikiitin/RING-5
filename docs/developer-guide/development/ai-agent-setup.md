---
title: "AI Agent Setup"
parent: Development
grand_parent: Developer Guide
nav_order: 6
---

# AI Agent Setup

<!-- markdownlint-disable MD024 -->

Guide to configuring AI coding assistants for RING-5 development.

## Overview

The canonical, verified project guide for AI assistants is **[`/CLAUDE.md`](../../../CLAUDE.md)** at
the repository root, with task-specific recipes under
**[`/.claude/skills/`](../../../.claude/skills/)**:

- `add-plot-type`
- `add-shaper`
- `parsing-and-variable-types`
- `rendering-figureconfig`
- `e2e-streamlit-testing`

`CLAUDE.md` is the single source of truth for architecture, layer boundaries, commands, conventions,
gotchas, and extension recipes — read it first. Everything else on this page is supporting detail.

## Supported AI Assistants

- **Claude Code** (primary) — reads `CLAUDE.md` and `.claude/skills/` automatically. Project-scoped
  MCP servers live in `.mcp.json`:
  - `context7` — up-to-date library docs for fast-moving deps (Streamlit, Plotly, pandas, scipy,
    matplotlib). Ask with "use context7" when unsure of a current API.
  - `playwright` — drives a real browser; ideal for the Streamlit e2e/visual suite and for
    reproducing UI bugs interactively (pairs with the `e2e-streamlit-testing` skill).
- **GitHub Copilot** (VS Code, Neovim, JetBrains) — reads `.github/copilot-instructions.md`, which
  now **redirects to `/CLAUDE.md`** so both tools share one source of truth.
- **Other assistants** that support custom instructions — point them at `/CLAUDE.md`.

## Setup

### Claude Code

No configuration is required. Open the repository and Claude Code will load `CLAUDE.md` and the
`.claude/skills/` recipes automatically. On first use it will ask you to approve the project-scoped
MCP servers declared in `.mcp.json` (`context7`, `playwright`).

### GitHub Copilot

Copilot automatically reads `.github/copilot-instructions.md`, so once the extension is installed and
authenticated there is nothing else to configure — the instructions file redirects Copilot to
`CLAUDE.md`.

- **VS Code**: install the *GitHub Copilot* extension (Extensions → search "GitHub Copilot"),
  authenticate, and you are done.
- **Neovim** (vim-plug): add `Plug 'github/copilot.vim'`, then run `:Copilot setup`.

### Other assistants

For any other assistant that supports custom or project instructions, point it at the repository's
`/CLAUDE.md`. Do not maintain a separate, parallel instruction file — it will drift out of date.

## What the Guidance Provides

`CLAUDE.md` (and the redirecting `.github/copilot-instructions.md`) give AI assistants:

### 1. Project Context

- RING-5 mission and domain (gem5 simulation-output analysis).
- Layered, strictly typed architecture.
- Technology stack (Python 3.12+, Streamlit, Plotly, Matplotlib, pandas).

### 2. Design Principles

- Layer boundaries: `src/core/` and `src/parsing/` must not import Streamlit or touch
  `st.session_state`. The UI lives in `src/web/`.
- The facade entry point is `ApplicationAPI` in `src/core/application_api.py`.
- Design patterns: Strategy, Factory, Facade, Singleton.
- Test-driven workflow.

### 3. Coding Standards

- **Strong typing**: type hints are mandatory on all code.
- **Immutability**: never use `inplace=True` on DataFrames in `src/`. Always return new objects
  (`.copy()` first).
- **No bare `except:`** in `src/`. Catch specific exceptions; raise or log, never silently swallow.
- **Zero fabrication**: never guess data values. If a gem5 regex fails to match, raise or log.

### 4. Critical Rules

- ⛔ **Version control is human-only** — assistants never run `git add/commit/push/branch/...`.
- 📋 **Complete type annotations** required.
- 🎯 **No invented data** — real values only.
- 🧪 **Tests before declaring done** — run `make test` (and `make arch-check` /
  `make quality-gate` plus `./python_venv/bin/mypy src/`).

### 5. Common Workflows

- Adding shapers (`add-shaper` skill).
- Adding plot types (`add-plot-type` skill).
- Parsing and variable types (`parsing-and-variable-types` skill).
- Rendering / `FigureConfig` work (`rendering-figureconfig` skill).
- End-to-end Streamlit testing (`e2e-streamlit-testing` skill).

### 6. Domain Knowledge

- gem5 `stats.txt` format.
- Variable types (scalar, vector, distribution, histogram).
- gem5 conventions: 9 plot types (`snake_case` keys), 10 shapers (`camelCase` keys), the Wong
  default color palette, and the `{y}.sd` error-bar convention.

## Project Architecture for AI Tasks

When generating or refactoring code, assistants must respect the live layout:

- **Facade / entry point**: `src/core/application_api.py` (`ApplicationAPI`).
- **Services**: `src/core/services/{data_services,managers,visualization}/`.
- **Shapers**: implementations in `src/core/services/shapers/` (`factory.py`, `impl/`, `shaper.py`);
  their UI configuration panels in `src/web/components/shapers/`.
- **Parsing**: `src/parsing/` (with `src/parsing/gem5/`).
- **State**: core state in `src/core/state/` (`RepositoryStateManager` plus repositories); UI state
  in `src/web/state/ui_state_manager.py`.
- **Plotting**: `src/web/pages/ui/plotting/` (`plot_factory.py`, `base_plot.py`, `types/`,
  `styles/`, `utils/`, `plot_renderer.py`, `download_section.py`).
- **Rendering connectors**: `src/web/rendering/`
  (`plotly_connector.py`, `matplotlib_connector.py`, `trace_to_plotly.py`,
  `matplotlib_trace_renderer.py`); `FigureConfig` lives in `src/core/models/visualization/`, and the
  16-step `STYLING_PIPELINE_ORDER` is defined in `src/web/rendering/_connector_protocol.py`.
- **UI pattern**: **Components** (`src/web/components/`) + **Controllers**
  (`src/web/controllers/plot/`: `creation_controller.py`, `pipeline_controller.py`,
  `render_controller.py`). Chart display is handled by `ChartDisplayComponent` in
  `src/web/components/common/chart_display.py`.

## Using AI for Development

### Code Generation

**Request**: "Create a new filter shaper that filters rows by benchmark name."

**The assistant should**:

1. Create the shaper class in `src/core/services/shapers/impl/` with proper types.
2. Write unit tests first.
3. Implement the transformation logic (returning a new DataFrame, never `inplace=True`).
4. Register it in `src/core/services/shapers/factory.py`.
5. Add its UI configuration panel under `src/web/components/shapers/` if user-configurable.

### Bug Fixing

**Request**: "Fix the bug in the normalize shaper where division by zero occurs."

**The assistant should**:

1. Read the existing code.
2. Add a test for the edge case.
3. Fix the implementation.
4. Verify all tests pass (`make test`).

### Refactoring

**Request**: "Refactor the plot factory to use type-based dispatch."

**The assistant should**:

1. Maintain the existing API.
2. Update all usages.
3. Keep architectural layer boundaries intact (no Streamlit imports leaking into `src/core/`).
4. Run the full test suite.

## Best Practices

### 1. Be Specific

- **Good**: "Create a shaper that normalizes values to range [0, 1] using min-max scaling."
- **Bad**: "Add normalization."

### 2. Request Tests First

- **Good**: "Write tests for a shaper that calculates the geometric mean, then implement it."
- **Bad**: "Implement geometric mean shaper."

### 3. Verify Outputs

Always:

- Run the generated tests (`make test`).
- Type-check with mypy (`./python_venv/bin/mypy src/`).
- Run `make arch-check` to confirm layer boundaries are respected.
- Review the code for architectural compliance.

### 4. Iterate

If output does not match patterns:

- Point out the specific issue.
- Reference existing similar code.
- Ask for corrections.

## Example Interactions

### Adding a Feature

**You**: "I need a shaper that calculates speedup relative to a baseline. Follow TDD."

**The assistant should**:

1. Write a test:

   ```python
   def test_speedup_basic() -> None:
       data = pd.DataFrame({"ipc": [1.0, 2.0], "baseline": [1.0, 1.0]})
       config = {"metric": "ipc", "baseline": "baseline"}
       shaper = SpeedupShaper(config)
       result = shaper(data)
       assert result["speedup"].tolist() == [1.0, 2.0]
   ```

2. Implement the shaper in `src/core/services/shapers/impl/`.
3. Run the tests.
4. Register it in `src/core/services/shapers/factory.py`.

### Debugging

**You**: "The grouped bar plot isn't showing multiple groups correctly."

**The assistant should**:

1. Read the grouped-bar implementation under `src/web/pages/ui/plotting/types/`.
2. Check the data structure flowing through the controllers.
3. Add a debug test case.
4. Fix the grouping logic.
5. Verify with the test.

### Refactoring

**You**: "The plot configuration code has lots of duplication. Refactor it."

**The assistant should**:

1. Identify the common patterns.
2. Extract helper functions.
3. Update all call sites.
4. Ensure tests still pass.
5. Type-check all changes.

## Troubleshooting

### AI Not Following Guidelines

**Issue**: the assistant suggests code that violates RING-5 patterns.

**Solution**:

- Explicitly reference `/CLAUDE.md` and the relevant skill in `.claude/skills/`.
- Quote the specific rule: "Follow the layer-boundary rule — `src/core/` must not import Streamlit."
- Show an example from existing code.

### AI Suggests Git Commands

**Issue**: the assistant tries to commit or push.

**Solution**:

- Remind it: "Version control is human-only per project rules — never run git mutations."
- The assistant should only suggest code changes, not perform version control.

### Missing Type Hints

**Issue**: generated code lacks type annotations.

**Solution**:

- Request: "Add complete type hints."
- Run: `./python_venv/bin/mypy src/`.

## Advanced Usage

### Batch Operations

**Request**: "Create test cases for the sort shaper covering edge cases."

**The assistant generates** tests for an empty DataFrame, a single row, duplicate values, null
values, and a large dataset.

### Architecture Questions

**Request**: "Should this shaper go in the core layer or the web layer?"

**The assistant should**:

- Reference the layer boundaries in `CLAUDE.md`.
- Explain that shaper logic belongs in `src/core/services/shapers/` while its configuration UI
  belongs in `src/web/components/shapers/`.
- Recommend the correct location.

### Code Review

**Request**: "Review this plot implementation for RING-5 compliance."

**The assistant checks**:

- Type-hint completeness.
- Architectural layer boundaries (`make arch-check`).
- Test coverage.
- Error handling (no bare `except:`).
- Documentation.

## Limitations

AI assistants:

- ❌ Cannot run git mutations (version control is human-only).
- ❌ Cannot deploy code.
- ❌ May miss context from other files.
- ✅ Can generate code following project patterns.
- ✅ Can write tests.
- ✅ Can refactor existing code.
- ✅ Can explain the architecture.

Always verify AI-generated code through testing (`make test`) and type checking
(`./python_venv/bin/mypy src/`).

## Next Steps

- Development setup: [setup.md](setup.md)
- Testing: [testing.md](testing.md)
- Code quality: [code-quality.md](code-quality.md)
- Contributing: [../../../CONTRIBUTING.md](../../../CONTRIBUTING.md)
