---
title: "Code Quality Tools"
parent: Development
grand_parent: Developer Guide
nav_order: 3
---

# Code Quality Tools

RING-5 keeps tool versions in `pyproject.toml` and exposes repeatable commands
through the Makefile. The same quality gate runs locally and in CI.

## Toolchain

| Tool | Version | Purpose |
|---|---:|---|
| Black | 26.5.1 | Deterministic Python formatting |
| Flake8 | 7.3.0 | Style and correctness linting |
| MyPy | 2.3.0 | Static type checking |
| Bandit | 1.9.4 | Python security analysis |
| pip-audit | 2.10.1 | Installed-package vulnerability audit |

Black and Flake8 use a 100-character line limit. MyPy targets Python 3.12,
requires typed function definitions, rejects implicit optionals, and checks
untyped bodies. Third-party stubs are declared in the development extra.

Bandit scans `ring5/` and `src/` for medium- and high-severity findings.
`B404` and `B603` are excluded because the parser intentionally launches a
validated Perl command without a shell.

## Semantic checks

Generic linters cannot enforce all repository contracts, so the project ships
three dependency-free checks in `scripts/`.

### Architecture

```bash
make arch-check
```

`check_architecture.py` parses imports and syntax to enforce layer boundaries,
keep Streamlit state out of core code, prohibit unsafe constructs, and preserve
immutable DataFrame operations.

### Public documentation

```bash
make docs-check
```

`check_public_docstrings.py` requires docstrings on public modules, classes,
functions, and methods. When a Google-style `Args` section is present, its
parameter names must match the signature. `check_doc_links.py` validates local
Markdown targets throughout the contributor and user documentation.

### Comments

```bash
make comments-check
```

`check_comments.py` tokenizes Python comments and rejects assistant-specific
references, internal milestone labels, and drafting slogans. Comments should
explain intent, constraints, or non-obvious behavior—not narrate statements or
record change history.

### Dependencies

```bash
make dependency-check
```

`analyze_dependencies.py` compares production imports with declared runtime
dependencies. The target also runs `pip check` to detect incompatible or missing
installed packages.

## Commands

Format the repository:

```bash
make format
```

Run individual checks:

```bash
make format-check
make lint
make type-check
make arch-check
make comments-check
make docs-check
make dependency-check
make security-audit
```

Run the complete gate before pushing:

```bash
make quality-gate
```

The gate runs architecture, comment, documentation, dependency, formatting,
lint, type, Bandit, and vulnerability checks. Build validation is separate:

```bash
make package-check
```

## Pre-commit

Install and run repository hooks with:

```bash
make pre-commit-install
make pre-commit
```

Pre-commit combines the quality tools above with file-format, merge-marker,
large-file, debug-statement, private-key, and filename-case checks. It also
blocks direct commits to `main`.

## See also

- [Testing](testing.md)
- [CI/CD pipeline](ci-cd.md)
- [Architecture overview](../architecture/overview.md)
- [Layer boundaries](../architecture/layer-boundaries.md)
