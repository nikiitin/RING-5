---
layout: default
title: Testing
parent: Development
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/development/testing/
redirect_from:
  - /engineering-reference/development/testing-patterns/
---

# Testing

Place a test at the lowest layer that proves the contract without hiding a cross-component failure.

| Location | Scope |
| --- | --- |
| `tests/unit/` | Core, parser, rendering, and public helpers in isolation |
| `tests/integration/` | Cross-component workflows and the supported `ring5` API |
| `tests/ui_logic/` | UI decisions separated from Streamlit rendering |
| `tests/ui_unit/` and `tests/ui/` | Streamlit components and pages with mocked boundaries |
| `tests/e2e/` | Browser workflows against a running application |
| `tests/performance/` | Explicit performance contracts |
| `tests/tests_principle_compliance/` | Architecture and design invariants |
| `tests/visual/` | Manual visual diagnostics; excluded from the default pytest collection |

Reuse fixtures from `tests/conftest.py` and existing xdist groups for shared state. Tests should
assert public outcomes and typed errors, not implementation call order unless orchestration is the
contract.

## Performance regression checks

<!--
`uman~ring5.quality.performance-regression-gates.documentation~1`

Covers:
- req~ring5.quality.performance-regression-gates~1

-->

Performance tests use repeatable fixtures and explicit thresholds for large-data transformations,
caches, rendering, and worker-pool throughput. Treat a threshold change as a reviewed contract
change rather than weakening it merely to accommodate a regression. They live outside the default
test targets and run explicitly with `python_venv/bin/pytest tests/performance -n 0 --no-cov`.

## Commands

```bash
make test-unit        # fast unit and UI-unit tests
make test             # non-browser tests plus serial Plotly export tests
make test-ci          # non-browser suite with coverage enforcement
make test-export      # serial Kaleido export tests
make test-latex       # PGF tests; requires XeLaTeX
make test-e2e         # Playwright workflows
make test-visual      # local visual diagnostics
```

Use markers declared in `pyproject.toml`. Plotly/Kaleido export and other process-owning tests run
serially. Browser tests use the Chromium installed by `make dev`.

For a public API addition, extend `tests/integration/test_ring5_public_api.py`. For serialized
changes, test both current output and loading or migrating an older fixture.
