---
layout: default
title: Development Troubleshooting
parent: Development
grand_parent: Developer Guide
nav_order: 6
permalink: /developer-guide/development/troubleshooting/
---

# Development troubleshooting

## The environment is inconsistent

Run `python_venv/bin/python --version` and `python_venv/bin/pip check`. Re-run `make dev` after a
dependency change. Do not mix a globally installed command with modules from `python_venv`.

## Tests cannot find fixture data

Run `make test-data mock-data`. The targets download the versioned integration archive when absent
and generate mock CSV fixtures. Do not commit generated test data unless a test explicitly owns the
fixture.

## A parallel test is intermittent

Re-run the focused test with `-n 0`. If it owns a browser process, portfolio directory, process pool,
or other shared resource, use the existing serial marker or xdist group rather than a timing sleep.

## Kaleido or PGF export fails

Use `make test-export` for serial Kaleido tests. Install Chromium with `make playwright-install` or
the environment-specific Kaleido command. For PGF, run `make check-latex` before `make test-latex`.

## The architecture check rejects an import

Read [Layer Boundaries](../architecture/layer-boundaries/). Move shared data to models, domain logic
to core services, UI rendering to components, or inject a protocol/callback from a composition root.
Do not bypass the AST check with a dynamic import.

## A portfolio test affects local data

Set `RING5_DATA_DIR` to a temporary directory before constructing application services. Tests should
use fixtures that isolate and reset `PathService` caches.
