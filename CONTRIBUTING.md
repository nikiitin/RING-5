# Contributing to RING-5

RING-5 welcomes focused bug fixes, documentation improvements, new simulator support, and plotting
features. Repository-specific architecture rules are summarized in [`AGENTS.md`](AGENTS.md).

## Development setup

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make pre-commit-install
```

`make dev` creates `python_venv`, installs the exact development dependencies, installs Chromium,
and prepares test fixtures. Python 3.12, 3.13, and 3.14 are supported by CI.

## Workflow

1. Create a branch from `main`.
2. Inspect existing tests and documentation for the affected behavior.
3. Implement the smallest coherent change and add focused tests.
4. Update user or developer documentation when a public contract changes.
5. Run the local verification commands.
6. Review the complete diff before opening a pull request.

Use conventional commit subjects where practical: `feat`, `fix`, `docs`, `test`, `refactor`,
`perf`, `build`, or `chore`.

## Verification

During development, run focused tests such as:

```bash
python_venv/bin/pytest tests/unit/test_target.py -n 0
python_venv/bin/mypy path/to/changed_module.py
```

Before opening a pull request, run:

```bash
make quality-gate
make test-ci
make test-e2e
make package-check
```

Plotly/Kaleido export tests are marked `serial` and must run with `-n 0`. Browser tests require the
Playwright Chromium installation provided by `make dev`.

## Code standards

- Add complete type annotations to production functions.
- Use concise Google-style docstrings for public classes, functions, parameters, return values,
  and meaningful exceptions.
- Keep comments for intent, constraints, and non-obvious decisions. Do not narrate the code or
  preserve change history in comments.
- Do not mutate caller-owned DataFrames or configuration dictionaries.
- Catch specific exceptions and preserve the original exception as `__cause__` at public boundaries.
- Keep core and parsing code independent from Streamlit and `src.web`.
- Expose supported scripting functionality through `ring5/`; user code should not import `src.*`.

The semantic checks in `scripts/check_architecture.py`, `scripts/check_comments.py`, and
`scripts/check_public_docstrings.py` enforce the principal boundaries.

## Tests

- Unit tests belong in `tests/unit/`.
- Cross-component and public API workflows belong in `tests/integration/`.
- Streamlit logic and component tests belong in `tests/ui_logic/` and `tests/ui_unit/`.
- Browser workflows belong in `tests/e2e/`.
- Reuse fixtures from `tests/conftest.py` and existing xdist groups for shared state.
- Test both Plotly and Matplotlib when traces, figure configuration, or export behavior changes.
- Add migration tests when serialized portfolio or pipeline formats change.

## Extension guides

Detailed recipes are available for common changes:

- [Add a plot type](.agents/skills/add-plot-type/SKILL.md)
- [Add a shaper](.agents/skills/add-shaper/SKILL.md)
- [Extend parsing](.agents/skills/parsing-and-variable-types/SKILL.md)
- [Modify rendering](.agents/skills/rendering-figureconfig/SKILL.md)
- [Write browser tests](.agents/skills/e2e-streamlit-testing/SKILL.md)

## Pull requests

Describe the problem, behavior change, compatibility impact, and verification performed. Include
screenshots for visible UI changes and representative output for parser or export changes. Keep the
branch free of generated files, local settings, credentials, plans, and unrelated formatting churn.
