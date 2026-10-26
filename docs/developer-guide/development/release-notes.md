---
layout: default
title: Release Notes
parent: Development
grand_parent: Developer Guide
nav_order: 8
permalink: /developer-guide/development/release-notes/
---

# Release notes

## Unreleased

### Documentation and deployment

- GitHub Pages and pull-request CI install the locked root Bundler environment, build the
  complete Just the Docs site, and audit generated routes, redirects, assets, and internal links.
- `make docs-audit` reproduces the generated-site check after `make docs-build`.

### Packaging

- Wheels and source distributions include the Perl scanner/parser runtime and the custom
  Plotly component. `make package-check` verifies those files in both archive formats.

### Scanning and parsing

- `scan_limit=0` selects every matching file, up to the 10,000-file discovery safety ceiling.
  The web Quick and Deep Scan controls remain bounded samples of 10 and 256 files.
- Escaped and unescaped literal punctuation in numeric pattern names resolves consistently;
  `system.cpu\d+.ipc` and `system\.cpu\d+\.ipc` identify the same pattern.
- The Perl scanner rejects files exceeding its scan-line budget (1,000,000 lines by default).
  Aggregated scan results include submitted and successful file counts, and the public API rejects
  partial scans with `ScanError`.
- Parser submission enforces aggregate file, byte, variable, file-variable, regex-candidate,
  regex-attempt, line-count, and elapsed-time bounds. Parse batches that exceed ten minutes fail
  with `ParseError`; cancellation is requested for unfinished work. Perl backend errors propagate
  as parse failures.
- A numeric pattern that exceeds `RING5_MAX_VAR_REPEAT` fails visibly. The default limit is
  1,024 instances; `0` disables this cap for trusted inputs.

### Web filesystem policy

- Browser-submitted statistics paths are confined to `RING5_ALLOWED_STATS_ROOTS`. When unset, the
  launch working directory is the only root, which also gives installed-package launches a stable
  default. The Data Source page displays the active roots and rejected paths include remediation.

### Deployment and workload requirements

- Deployments that read result trees outside their launch directory must set
  `RING5_ALLOWED_STATS_ROOTS` before starting Streamlit.
- For workloads that exceed a resource limit, split or narrow the input and handle
  `ScanError` or `ParseError` in scripts.
- Pattern filters are intentionally narrow: literal ASCII letters and digits, `.`, `_`, `:`, and
  `\d+` placeholders are accepted; arbitrary regular-expression operators are rejected.
