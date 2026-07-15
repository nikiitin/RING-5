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

- GitHub Pages and pull-request CI now install the locked root Bundler environment, build the
  complete Just the Docs site, and audit generated routes, redirects, assets, and internal links.
- `make docs-audit` reproduces the generated-site check after `make docs-build`.

### Packaging

- Wheels and source distributions now include the Perl scanner/parser runtime and the custom
  Plotly component. `make package-check` verifies those files in both archive formats.

### Scanning and parsing

- `scan_limit=0` again means every matching file, up to the 10,000-file discovery safety ceiling.
  The web Quick and Deep Scan controls remain bounded samples of 10 and 256 files.
- Escaped and unescaped literal punctuation in numeric pattern names now resolves consistently;
  `system.cpu\d+.ipc` and `system\.cpu\d+\.ipc` identify the same pattern.
- The Perl scanner now fails an oversized file instead of silently returning variables from only
  its first one million lines. Aggregated scan results include submitted and successful file counts,
  and the public API rejects partial scans with `ScanError`.
- Parser submission now enforces aggregate file, byte, variable, file-variable, regex-candidate,
  regex-attempt, line-count, and elapsed-time bounds. Parse batches that exceed ten minutes fail
  with `ParseError`; cancellation is requested for unfinished work. Perl backend errors no longer
  appear as successful empty parses.
- A numeric pattern that expands beyond `RING5_MAX_VAR_REPEAT` now fails visibly instead of being
  omitted. The default is 1,024 instances; `0` disables this cap for trusted inputs.

### Web filesystem policy

- Browser-submitted statistics paths are confined to `RING5_ALLOWED_STATS_ROOTS`. When unset, the
  launch working directory is the only root, which also gives installed-package launches a stable
  default. The Data Source page displays the active roots and rejected paths include remediation.

### Migration notes

- Deployments that read result trees outside their launch directory must set
  `RING5_ALLOWED_STATS_ROOTS` before starting Streamlit.
- Scripts that depended on a partial scan or parse after a resource limit must split or narrow the
  workload and handle `ScanError` or `ParseError`.
- Pattern filters are intentionally narrow: literal ASCII letters and digits, `.`, `_`, `:`, and
  `\d+` placeholders are accepted; arbitrary regular-expression operators are rejected.
