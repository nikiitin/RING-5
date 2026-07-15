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
| `make security-audit` | Bandit and dependency vulnerability audit |

Run a focused tool while editing, then the aggregate target before review. Do not silence a check
without documenting why the exception preserves the underlying contract.

Public functions use typed errors from `ring5.errors` and concise Google-style docstrings. Keep
comments for intent, invariants, and non-obvious constraints; Git history carries change narration.

`make pre-commit` runs repository hooks over all files. Hooks are useful feedback, but the Make
targets remain the documented local interface and match CI more closely.
