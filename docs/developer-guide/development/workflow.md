---
layout: default
title: Contributor Workflow
parent: Development
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/development/workflow/
redirect_from:
  - /engineering-reference/development/
  - /engineering-reference/quick-reference/
  - /engineering-reference/quick-reference/common-tasks/
  - /engineering-reference/quick-reference/file-locations/
  - /engineering-reference/quick-reference/naming-conventions/
---

# Contributor workflow

## Before editing

1. Read [`AGENTS.md`](../../../AGENTS.md) and the extension recipe for the area, if one exists.
2. Locate the owning layer and its protocols with [Layer Boundaries](../architecture/layer-boundaries/).
3. Read the implementation, focused tests, serialized models, and public documentation.
4. Record any compatibility surface: public Python name, CLI option, UI label, plot or shaper
   identifier, portfolio schema, or parser CSV output.

## Implement

Keep the change within the owning layer. Add a narrow protocol only where a real boundary or test
seam needs one. DataFrame operations return new objects. Parser and scan failures remain visible.

Update user documentation for observable behavior and developer documentation for contracts. Add a
migration and tests before changing serialized identifiers or portfolio fields.

## Verify while working

Run the smallest test and semantic check that exercise the change:

```bash
python_venv/bin/pytest tests/unit/test_target.py -n 0 --no-cov
make arch-check
make docs-check
```

Use `-n 0` for a focused test whose process or browser resources cannot run in parallel. Exercise
both Plotly and Matplotlib when changing traces, resolved figure configuration, or export behavior.

## Review before opening a pull request

Run the applicable full gates:

```bash
make quality-gate
make test-ci
make test-e2e
make package-check
```

Inspect the complete diff for generated files, local application data, credentials, stale paths,
and unrelated edits. In the pull request, state the problem, compatibility impact, tests, and any
manual verification. Include a screenshot only for a visible UI change.
