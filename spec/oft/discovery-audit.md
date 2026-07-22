# RING-5 feature-discovery convergence audit

This audit explains how the current OpenFastTrace inventory was discovered and why the review is
considered converged. It is a decision log, not generated output. The normative requirements and
evidence remain in `inventory.json`.

## Scope and acceptance rule

The review covers behavior available through the Streamlit application, supported Python API and
CLI, registered parsers, managers and shapers, rendering and export boundaries, portfolio
reproducibility, extension contracts, and application quality invariants that constrain those
features.

A candidate becomes a current requirement when it has an active implementation path and either a
focused test or a stable public/user-facing contract. Closely related controls are grouped into one
behavioral requirement: for example, legend spacing fields belong to legend configuration rather
than becoming one requirement per numeric widget. Dormant helpers, removed screens, stale tests,
and controls that do not affect output are not described as current features.

## Surfaces reviewed

The converged pass inspected:

- all 59 Markdown documentation sources and the five live navigation destinations;
- all 260 Python modules under `src/` and `ring5/`, including the public package exports;
- all 318 Python files under `tests/`, with focused review of the 285 `test_*.py` suites;
- all 333 direct Streamlit control calls across 57 web modules;
- plot, shaper, simulator and statistic registries;
- parser strategies, variable types, internal statistic names and default file patterns;
- public `Session`, `Table`, figure-builder, decoration and asynchronous-job members;
- `ApplicationAPI` and its manager, data-service and shaper sub-APIs;
- CLI commands and command-qualified options;
- parse, scan, restore, shaper and figure configuration schemas.

The generator binds 556 live values from 45 discovery sources to explicit requirements. A new or
renamed value makes `make oft-check` fail until the inventory records a decision.

## Convergence runs

<!--
`uman~ring5.trace.discovery-convergence.documentation~1`

Covers:
- req~ring5.trace.discovery-convergence~1

-->

| Run | Independent review route | New requirements | Inventory after run |
| --- | --- | ---: | ---: |
| Baseline | Existing docs, main workflows and central registries | 126 total baseline requirements | 126 |
| 1 | Documentation/navigation replay plus parser, service, UI and test cross-check | 23 | 149 |
| 2 | Public API/schema inventory plus every active control and test-module replay | 7 | 156 requirements |
| Governance | Added this convergence requirement and expanded automatic drift sources | 1 | 157 |
| 3 | Repeated run 2 after all accepted changes, including rejected-candidate recheck | 0 | 157 |
| Requested addition | HTML coverage report based on native OFT output | 1 | 158 |

Run 1 accepted configurable application storage, CSV delimiter and metadata handling, authorized
web roots, quick/deep scan progress, pattern-index selection, statistics-only parsing, entry and
summary selection, distribution range scanning, histogram rebinning, persistent workers, saved
pipeline configurations, plot filters, stack totals, heatmap summary controls, cumulative
histograms, Matplotlib TeX selection, public plot validation, data-manager and settings extension
contracts, the application facade, bounded caching, safe output formatting, and performance gates.

Run 2 accepted parser output aliases, configuration-variable fallbacks, Plotly hover behavior,
alternate category shading, Plotly export scaling, conversion of an existing plot to another type,
and per-series visual styling. It also corrected the group-cardinality and group-predicate wording
to match their implemented distinct-count and baseline-row semantics; corrections did not create
new requirements.

Run 3 used the same source categories and candidate rules as run 2. It produced no unbound live
surface and no additional behavior meeting the acceptance rule. This is the convergence point for
that discovery audit. The later HTML-report requirement is an explicitly requested feature rather
than a capability missed by the converged pass; future code changes can invalidate the inventory
through the drift check.

## Rejected and consolidated candidates

The following were reviewed explicitly so a later audit does not rediscover them as unexplained
gaps:

| Candidate | Decision |
| --- | --- |
| Performance and Workspace pages | Removed navigation destinations. Visual tests explicitly verify their absence; stale AppTest names are not application features. |
| Direct browser CSV upload | The legacy file uploader was removed. Existing CSVs enter through the recent pool or supported Python API; helper fixtures that stage files do not restore a web uploader. |
| CSV, JSON and Excel `DataComponents.download_buttons` | Dormant helper called only by its unit test. The active table offers filtered CSV download, which is inventoried. |
| Line-shape selector | The control stores a value but trace construction and both connectors do not consume it. It is not claimed as a working current feature. |
| Portfolio pipeline-template section | Stale test naming; the active portfolio page has no template section. Saved shaper configurations are inventoried separately. |
| Arbitrary Matplotlib TeX preamble | Intentionally disabled at the web boundary and covered by safe-output requirements. TeX engine selection remains supported. |
| Custom keyboard shortcuts | Explicitly absent; browser, Streamlit and Plotly defaults are not RING-5 features. |
| Per-widget legend, axis and label fields | Consolidated under the cohesive legend, axes, typography, data-label and series-style requirements; their typed fields are still drift-bound individually. |
| Pivot extraction controls | Consolidated under pivot-longer, whose requirement already includes extraction, selection, discard and merge behavior; its complete typed schema is drift-bound. |

## Reproduction

From the repository root:

```shell
make oft-generate
make oft-check
make oft-trace
make oft-trace-all
```

Reviewers should repeat the implementation, UI, public-surface and test passes when a drift failure
occurs or when a feature bypasses a central registry. Add the accepted delta and rejected decisions
here, then continue until a pass produces no new current requirements.
