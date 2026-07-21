# RING-5 future-feature delivery map

`006-development` is the integration branch. Each row uses a dedicated branch and one primary OFT
requirement. Dependencies name requirements that must be approved first.

Every feature follows the same acceptance sequence:

1. Confirm the requirement and serialized-data compatibility constraints.
2. Add domain models and services without presentation-layer dependencies.
3. Add a documented `ring5` API when the behavior is useful outside the web application.
4. Add the web workflow and migration support where persisted state changes.
5. Add unit, integration, rendering, and browser tests required by the affected surfaces.
6. Add user and developer documentation, exact OFT markers, and approved evidence.
7. Run focused checks, `make quality-gate`, `make test`, `make oft-trace`, and affected browser tests.

## Analysis and data foundations

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `analysis.regression-comparison` | `006-regression-comparison` | — |
| `analysis.statistical-comparison` | `006-statistical-comparison` | `analysis.regression-comparison` |
| `analysis.regression-annotations` | `006-regression-annotations` | `analysis.regression-comparison` |
| `data.multi-dataset-workspace` | `006-multi-dataset-workspace` | — |
| `data.lineage-undo-redo` | `006-data-lineage-undo-redo` | `data.multi-dataset-workspace` |
| `data.quality-profiler` | `006-data-quality-profiler` | — |
| `data.schema-contracts` | `006-data-schema-contracts` | `data.quality-profiler` |
| `data.validated-joins` | `006-data-validated-joins` | `data.multi-dataset-workspace`, `data.schema-contracts` |
| `data.semantic-units` | `006-semantic-units` | `data.schema-contracts` |
| `data.dataset-snapshots` | `006-data-dataset-snapshots` | `data.multi-dataset-workspace`, `data.lineage-undo-redo` |
| `workspace.background-jobs` | `006-background-jobs` | — |

## Plotting and figure composition

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `plots.multi-panel-dashboard` | `006-plots-multi-panel-dashboard` | — |
| `plots.linked-selections` | `006-plots-linked-selections` | `plots.multi-panel-dashboard` |
| `plots.drill-down` | `006-plots-drill-down` | `plots.linked-selections` |
| `plots.small-multiples` | `006-plots-small-multiples` | — |
| `plots.copy-settings-pipeline` | `006-plots-copy-settings-pipeline` | — |
| `plots.configuration-comparison` | `006-plots-configuration-comparison` | `plots.copy-settings-pipeline` |
| `figure.panel-composition` | `006-panel-composition` | `plots.multi-panel-dashboard` |
| `figure.accessible-themes` | `006-accessible-themes` | — |
| `figure.theme-presets` | `006-theme-presets` | `figure.accessible-themes` |
| `figure.line-styles` | `006-line-styles` | — |
| `plot.box` | `006-plot-box` | — |
| `plot.violin` | `006-plot-violin` | `plot.box` |
| `plot.ecdf` | `006-plot-ecdf` | — |
| `plot.area` | `006-plot-area` | `figure.line-styles` |
| `plot.radar` | `006-plot-radar` | — |
| `plot.waterfall` | `006-plot-waterfall` | — |
| `plot.sankey` | `006-plot-sankey` | — |
| `plot.parallel-coordinates` | `006-plot-parallel-coordinates` | — |

## Ingestion and exchange

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `ingestion.import-preview` | `006-import-preview` | — |
| `ingestion.browser-upload` | `006-browser-upload` | `ingestion.import-preview` |
| `ingestion.remote-sources` | `006-remote-sources` | `ingestion.import-preview` |
| `ingestion.incremental-parsing` | `006-incremental-parsing` | `data.dataset-snapshots` |
| `ingestion.parser-playground` | `006-parser-playground` | `ingestion.import-preview` |
| `shaping.config-import-export` | `006-pipeline-exchange` | — |

## Reproducibility and automation

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `portfolio.analysis-recipes` | `006-analysis-recipes` | `shaping.config-import-export` |
| `portfolio.history-diff` | `006-portfolio-history` | — |
| `portfolio.environment-metadata` | `006-environment-metadata` | — |
| `portfolio.signed-manifests` | `006-signed-manifests` | `portfolio.environment-metadata` |
| `portfolio.portable-bundles` | `006-portable-bundles` | `portfolio.signed-manifests`, `data.dataset-snapshots` |
| `automation.script-notebook-export` | `006-script-notebook-export` | `portfolio.analysis-recipes` |
| `automation.batch-matrices` | `006-batch-matrices` | `portfolio.analysis-recipes`, `workspace.background-jobs` |
| `automation.machine-readable-regression` | `006-regression-results` | `analysis.regression-comparison` |
| `automation.ci-regression-gates` | `006-ci-regression-gates` | `automation.machine-readable-regression` |
| `export.batch-reports` | `006-batch-reports` | `figure.panel-composition`, `portfolio.environment-metadata` |
| `automation.scheduled-reporting` | `006-scheduled-reporting` | `export.batch-reports`, `workspace.background-jobs` |

## Workspace

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `workspace.global-search` | `006-workspace-search` | `data.multi-dataset-workspace` |
| `workspace.command-palette` | `006-command-palette` | `workspace.global-search` |
| `workspace.favorites-tags` | `006-favorites-tags` | `data.multi-dataset-workspace` |
| `workspace.collaborative-review` | `006-collaborative-review` | `portfolio.history-diff` |
| `workspace.autosave-recovery` | `006-autosave-recovery` | `portfolio.history-diff` |
| `workspace.guided-analysis` | `006-guided-analysis` | `analysis.regression-comparison`, `ingestion.import-preview` |

## Traceability

| Requirement | Branch | Dependencies |
| --- | --- | --- |
| `trace.future-status-reporting` | `006-oft-status-views` | — |
| `trace.branch-association` | `006-oft-branch-association` | `trace.future-status-reporting` |
| `trace.requirement-history` | `006-oft-requirement-history` | `trace.branch-association` |
| `trace.requirement-diff` | `006-oft-requirement-diff` | `trace.requirement-history` |
| `trace.readiness-checklist` | `006-oft-readiness` | `trace.future-status-reporting` |
| `trace.approval-gate` | `006-oft-approval-gate` | `trace.readiness-checklist` |
