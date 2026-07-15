# Contributing to RING-5

RING-5 accepts focused fixes, documentation improvements, plotting features, and simulator
support. Read [`AGENTS.md`](AGENTS.md) before changing code; it defines the architecture boundaries
and public API rules enforced by repository checks.

## Set up the repository

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make pre-commit-install
```

`make dev` creates `python_venv`, installs editable development, CI, and browser-test dependencies,
installs Playwright Chromium, and prepares test fixtures. CI supports Python 3.12, 3.13, and 3.14.

## Make a change

1. Create a branch from `main`.
2. Read the implementation, tests, and documentation for the affected behavior.
3. Make one coherent change and add focused tests.
4. Update the User Guide for observable behavior or the Developer Guide for internal contracts.
5. Run focused checks, then the applicable repository gates.
6. Inspect the complete diff before opening a pull request.

Use a conventional commit prefix when it fits: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`,
`build`, or `chore`.

## Verify the change

During development, run the smallest relevant test or check:

```bash
python_venv/bin/pytest tests/unit/test_target.py -n 0 --no-cov
python_venv/bin/mypy path/to/changed_module.py
make docs-check
```

Before opening a pull request, run:

```bash
make quality-gate
make test-ci
make test-e2e
make package-check
```

Run Plotly/Kaleido export tests serially through `make test-export`. Browser tests use the Chromium
installation provided by `make dev`.

## Follow project contracts

- Add type annotations to production functions and concise Google-style docstrings to public APIs.
- Keep `src/core/` and `src/parsing/` independent from Streamlit and `src.web`.
- Do not mutate caller-owned DataFrames or configuration mappings.
- Preserve specific failures and wrap public API failures in errors from `ring5.errors`.
- Expose scripting behavior through `ring5/`; user examples must not import `src.*`.
- Add migration coverage when a serialized portfolio or pipeline format changes.
- Test both rendering engines when traces, figure configuration, or export behavior changes.

The [Developer Guide](docs/developer-guide/index.md) explains the architecture and workflow. Recipes
for common extensions live under [`.agents/skills/`](.agents/skills/).

## Open the pull request

Describe the problem, the behavior or contract that changed, compatibility impact, and verification
performed. Include screenshots for visible UI changes and representative output for parser or
export changes. Exclude generated files, local settings, credentials, plans, and unrelated edits.
