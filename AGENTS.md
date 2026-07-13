# RING-5 contributor guide

This is the canonical repository guide for automated and human contributors. Keep it aligned with
the code and prefer links to detailed documentation over duplicating it here.

RING-5 (*Reproducible Instrumentation for Numerical Graphics for gem5*) turns simulator statistics
into publication-ready figures. It provides a Streamlit application, a headless Python API, and a
command-line interface. Python 3.12 or newer is required.

## Required invariants

1. `src/core/` and `src/parsing/` must not import Streamlit or access `st.session_state`.
2. Core code must not import `src.web`; `ring5/` and `app.py` are composition roots and may use both.
3. DataFrame operations return new objects. Do not use `inplace=True`.
4. Catch specific exceptions. Do not use bare `except`, `eval`, or `exec` in production code.
5. Parsing failures must remain visible. Never fabricate simulator values.
6. Parse and scan work uses the asynchronous submit/finalize contracts.
7. Public APIs use typed errors from `ring5.errors` and concise Google-style docstrings.

Run `make arch-check` after structural changes.

## Architecture

Dependencies flow in one direction:

```text
Presentation: app.py, src/web/
                     |
                     v
Domain:       src/core/services/, src/core/state/, src/core/common/
                     ^
                     |
Data:         src/parsing/, src/core/models/
```

- `src/core/application_api.py` is the application facade used by the web interface.
- `src/core/state/repository_state_manager.py` is the in-memory state boundary.
- `src/parsing/parser_protocol.py` defines simulator backends; gem5 is registered in
  `src/parsing/gem5/`.
- `src/web/pages/ui/plotting/` contains plot types and engine-independent trace construction.
- `src/web/rendering/` resolves figure configuration and renders through Plotly or Matplotlib.
- `ring5/` is the supported programmatic surface. It composes core services and rendering without
  exposing Streamlit.

More detail is available in `docs/developer-guide/architecture/` and
`docs/engineering-reference/architecture/`.

## Public API

Use `import ring5` in scripts. The common workflow is:

```python
import ring5

with ring5.Session() as session:
    data = session.load("results.csv")
    spec = ring5.FigureSpec(x="benchmark", y_columns=["ipc"], title="IPC")
    figure = session.plot("bar", data=data, config=spec, engine="matplotlib")
    session.export(figure, "figures/ipc.pdf")
```

Important public entry points:

- `ring5.Session`: parse, load, transform, plot, render, export, and portfolio operations.
- `ring5.FigureSpec`: typed configuration for common figure settings.
- `ring5.Table`: pandas-independent data handle for figure scripts.
- `ring5.render_portfolio`: reproduce every figure from a saved portfolio.
- `ring5.available_plot_types`: discover registered plot identifiers.
- `ring5.doctor` and `ring5.shutdown`: dependency checks and worker-pool cleanup.

Do not ask users to import from `src.*`. Add intended public functionality to `ring5/`, document it,
and cover it through `tests/integration/test_ring5_public_api.py`.

## Commands

Use the repository virtual environment and Make targets:

```bash
make dev
make run
make test-unit
make test
make test-ci
make test-e2e
make quality-gate
make arch-check
make pre-commit
```

Focused checks can use the tools in `python_venv/bin/`. Include `ring5/`, `src/`, and relevant tests
in formatting, linting, and type-checking commands. Plotly/Kaleido exports run serially because they
own browser processes.

## Extension points

Task-specific recipes live in `.agents/skills/`:

| Change | Guide |
| --- | --- |
| Add a plot type | `.agents/skills/add-plot-type/SKILL.md` |
| Add a shaper | `.agents/skills/add-shaper/SKILL.md` |
| Extend parsing | `.agents/skills/parsing-and-variable-types/SKILL.md` |
| Modify figure rendering | `.agents/skills/rendering-figureconfig/SKILL.md` |
| Test Streamlit with Playwright | `.agents/skills/e2e-streamlit-testing/SKILL.md` |
| Audit the public API | `.agents/skills/api-check/SKILL.md` |

Plots use snake-case registry identifiers such as `grouped_stacked_bar`. Shapers retain their
serialized camel-case identifiers such as `columnSelector`; changing these requires migration
support for saved portfolios and pipelines.

Every plot implementation must build engine-independent traces and render correctly through both
connectors. Every shaper must validate its configuration, avoid input mutation, and participate in
the discriminated configuration union.

## Tests and documentation

- Unit tests live in `tests/unit/`; cross-component workflows belong in `tests/integration/`.
- Streamlit logic and component tests live in `tests/ui_logic/` and `tests/ui_unit/`.
- Browser tests live in `tests/e2e/`; visual diagnostics are separated under `tests/visual/`.
- Reuse shared fixtures and `columns_side_effect` from `tests/conftest.py`.
- Use existing markers and xdist groups for shared process or portfolio state.
- Update user documentation for observable behavior and developer documentation for contracts.
- Documentation is written in the present tense. Historical discussion belongs only in
  `docs/developer-guide/architecture/history.md`.

## Review checklist

Before handing off a change:

1. Inspect the complete diff for generated files, credentials, local settings, stale paths, and
   unrelated edits.
2. Confirm public names, error messages, parameters, return values, and exceptions are documented.
3. Run focused tests during development, then the complete quality and test gates.
4. Exercise both rendering engines when figure configuration or traces change.
5. Verify old portfolio and pipeline formats still load, or add an explicit migration.
6. Keep comments for intent, constraints, and non-obvious reasoning; remove narration of the code.
