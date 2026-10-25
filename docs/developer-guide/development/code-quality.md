---
layout: default
title: Quality Checks
parent: Development
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/development/code-quality/
---

# Quality checks

`make quality-gate` runs semantic checks, dependency validation, formatting, linting, type checking,
and security audits with the repository environment.

| Target | Checks |
| --- | --- |
| `make arch-check` | Import boundaries and prohibited syntax through AST analysis |
| `make comments-check` | Stale, narrative, and suppression comments |
| `make docs-check` | Public docstrings plus documentation links and repository paths |
| `make dependency-check` | Declared production imports and installed-package consistency |
| `make format-check` | Black formatting without modifying files |
| `make lint` | Flake8 rules |
| `make type-check` | Mypy over `src` and `ring5` |
| `make security-audit` | Bandit and a strict audit of resolved project dependencies |

Make targets define the Python checks: Black formats code, Flake8 lints it, Mypy checks types,
and Bandit audits security. Their configuration lives in `pyproject.toml`; editor tools use
`python_venv`. Pylance provides completion without a second type-checking policy. Trunk runs
complementary checks for workflows, shell scripts, configuration, and secrets.

Run maintenance scripts from the repository root as modules, such as
`python_venv/bin/python -m scripts.check_doc_structure`. This gives each script the same import
context as tests and Make targets.

Run a focused tool while editing, then the aggregate target before review. Do not silence a check
without documenting why the exception preserves the underlying contract.

Public functions use typed errors from `ring5.errors` and concise Google-style docstrings. Keep
comments for intent, invariants, and non-obvious constraints; Git history carries change narration.

## Cache requirements

<!--
`uman~ring5.quality.bounded-caching.documentation~1`

Covers:
- req~ring5.quality.bounded-caching~1

-->

Shared caches are thread-safe, size-bounded, and either expire entries or key them with full-content
fingerprints. Cached DataFrames are returned through isolated copies. New caches need tests for
eviction, expiry, concurrency, mutation isolation, statistics, and explicit clearing.

`make pre-commit` runs repository hooks over all files. Hooks are useful feedback, but the Make
targets remain the documented local interface and match CI more closely.
