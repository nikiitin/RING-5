# User Guide Generation Plan

> **Target**: `docs/user-guide/`
> **Audience**: End-users of the RING-5 web application (researchers, engineers)

---

## 1. Overview

The user guide focuses on **how to use the application** — not how it works internally.
It is written for researchers who want to create publication-quality plots from their
simulator output without needing to understand the codebase.

This guide will largely **migrate and update** existing documentation from `docs/webapp/`,
`docs/plots/`, and `docs/api/` (the user-facing parts).

---

## 2. Generation Order & Dependencies

The user guide is generated from Phase A analysis, specifically:
- Step 08 (web pages) — for webapp usage documentation
- Step 10 (plotting) — for plot type guides
- Step 06 (shapers) — for data transformation guides
- Step 14 (export) — for download/export guides
- Step 17 (config/build) — for installation
- Step 20 (docs audit) — for content to migrate and fix
- **Steps 23-30 (E2E tests & media generation) — ALL media assets must be generated FIRST (Phase B0)**

> **CRITICAL**: Phase B0 (documentation media generation via E2E tests, steps 23-30) must
> complete before any webapp or plot guide page is written. Every page references specific
> screenshots and GIFs from `docs/user-guide/media/`.

---

## 3. Complete File Structure

```
docs/user-guide/
├── index.md                                # User guide homepage & quick navigation
│
├── media/                                  # ALL screenshots, GIFs, videos (Phase B0, steps 23-30)
│   ├── getting-started/                    # ~4 assets (step 23)
│   ├── data-source/                        # ~12 assets (step 23)
│   ├── data-managers/                      # ~10 assets (step 24)
│   ├── manage-plots/                       # ~21 assets (steps 25, 26, 27)
│   ├── plots/                              # ~14 assets (steps 25, 28)
│   ├── export/                             # ~5 assets (step 29)
│   ├── portfolio/                          # ~5 assets (step 30)
│   └── navigation/                         # ~3 assets (step 30)
│
├── getting-started/
│   ├── installation.md                     # System requirements, setup, verification
│   ├── quick-start.md                      # 5-minute first plot walkthrough
│   └── first-analysis.md                   # Complete first analysis tutorial
│
├── webapp/
│   ├── web-interface-overview.md           # All pages, navigation, general concepts
│   ├── data-source.md                      # Loading data: parse gem5 / upload CSV
│   ├── data-managers.md                    # Preprocessor, outlier removal, seeds reduction
│   ├── manage-plots.md                     # Creating and managing plots
│   ├── plot-settings.md                    # All settings (layout, typography, legend, etc.)
│   ├── export-download.md                  # Downloading plots in various formats
│   └── portfolios.md                       # Saving and loading sessions
│
├── plots/
│   ├── bar-charts.md                       # Simple bar charts
│   ├── grouped-bar-charts.md               # Grouped bar charts
│   ├── stacked-bar-charts.md               # Stacked bar charts
│   ├── grouped-stacked-bars.md             # Grouped-stacked bar charts
│   ├── line-plots.md                       # Line/time-series plots
│   ├── scatter-plots.md                    # Scatter/correlation plots
│   ├── histogram-plot.md                   # Distribution histograms
│   ├── heatmap-plot.md                     # Heatmap visualizations
│   └── dual-axis-bar-dot.md                # Dual-axis bar-dot plots
│
└── data-transformations/
    └── shaper-user-guide.md                # How to use shapers (non-technical)
```

---

## 4. File Generation Details

### 4.1 index.md
- **Source**: Migrated from docs/Home.md
- **Updates**: New directory structure, updated learning paths, correct navigation
- **Content**: Welcome, quick links, learning paths by audience

### 4.2 getting-started/installation.md
- **Source**: Migrated from docs/Installation.md
- **Updates**:
  - Remove PyYAML reference (replaced with stdlib json)
  - Verify Python 3.12+ requirement
  - Update dependency list from current pyproject.toml
  - Verify platform-specific instructions still work
- **Content**: System requirements, platform setup, verification steps

### 4.3 getting-started/quick-start.md
- **Source**: Migrated from docs/webapp/Quick-Start.md
- **Updates**: Verify all steps match current UI, remove any stale screenshots
- **Content**: 5-minute walkthrough from launch to first plot
- **Media**:
  - `media/getting-started/app-first-launch.png` — what you see on first load
  - `media/getting-started/quick-start-workflow.gif` — animated scan → parse → plot

### 4.4 getting-started/first-analysis.md
- **Source**: Migrated from docs/webapp/First-Analysis.md
- **Updates**: Verify workflow steps, update any changed UI elements
- **Content**: Complete beginner tutorial
- **Media**:
  - `media/getting-started/first-plot-result.png` — final result screenshot

### 4.5 webapp/web-interface-overview.md
- **Source**: Migrated from docs/webapp/Web-Interface.md
- **Updates**:
  - REMOVE Performance page references (feature removed)
  - Update page list to match current navigation
  - Update state management description
  - Verify all UI descriptions match current implementation
- **Content**: Complete page catalog and UI overview
- **Media**:
  - `media/navigation/sidebar-navigation.png` — sidebar with all pages
  - `media/navigation/page-transitions.gif` — animated page navigation

### 4.6-4.11 webapp/ section
- **Source**: Migrated from docs/webapp/pages/ and docs/webapp/
- **Updates**: Verify against current codebase, fix any outdated references
- **Note**: Creating-Plots.md content merges into manage-plots.md and plot-settings.md
- **Media per page**:
  - data-source.md → `media/data-source/*.png` + `media/data-source/*.gif` (12 assets)
  - data-managers.md → `media/data-managers/*.png` + `media/data-managers/*.gif` (10 assets)
  - manage-plots.md → `media/manage-plots/*.png` + `media/manage-plots/*.gif` (21 assets)
  - plot-settings.md → `media/manage-plots/settings-*.png` (10 settings panel screenshots)
  - export-download.md → `media/export/*.png` + `media/export/*.gif` (5 assets)
  - portfolios.md → `media/portfolio/*.png` + `media/portfolio/*.gif` (5 assets)

### 4.12-4.20 plots/ section
- **Source**: Migrated from docs/plots/
- **Updates**:
  - Verify configuration options match current code
  - Add missing plot types (heatmap, dual-axis if not documented)
  - Remove any internal references (.agent/ paths)
  - Add split categories (grouped-bar-charts, stacked-bar-charts separate files)
- **Content**: Per-type usage guide with configuration options and examples
- **Media per plot type**:
  - Each plot type page → `media/plots/{type}-example.png` (rendered example)
  - Key plot types → `media/plots/{type}-creation.gif` (animated creation workflow)
  - `media/plots/plotly-interactive.gif` — Plotly hover/zoom demonstration
  - `media/plots/matplotlib-publication.png` — Matplotlib publication-ready output

### 4.21 data-transformations/shaper-user-guide.md
- **Source**: Migrated from docs/api/Data-Transformations.md
- **Updates**: Verify shaper list, add any new shapers, remove technical API details
- **Content**: Non-technical guide to data transformations

---

## 5. Migration Map

| Old Location | New Location | Action |
|-------------|-------------|--------|
| docs/Home.md | docs/user-guide/index.md | Migrate + Update |
| docs/Installation.md | docs/user-guide/getting-started/installation.md | Migrate + Fix deps |
| docs/webapp/Quick-Start.md | docs/user-guide/getting-started/quick-start.md | Migrate + Verify |
| docs/webapp/First-Analysis.md | docs/user-guide/getting-started/first-analysis.md | Migrate + Verify |
| docs/webapp/Web-Interface.md | docs/user-guide/webapp/web-interface-overview.md | Migrate + Remove deprecated |
| docs/webapp/pages/Data-Source.md | docs/user-guide/webapp/data-source.md | Migrate + Verify |
| docs/webapp/pages/Data-Managers.md | docs/user-guide/webapp/data-managers.md | Migrate + Verify |
| docs/webapp/pages/Manage-Plots.md | docs/user-guide/webapp/manage-plots.md | Migrate + Verify |
| docs/webapp/pages/Plot-Settings.md | docs/user-guide/webapp/plot-settings.md | Migrate + Verify |
| docs/webapp/Creating-Plots.md | (merged into manage-plots.md + plot-settings.md) | Merge + Verify |
| docs/webapp/Download-Guide.md | docs/user-guide/webapp/export-download.md | Migrate + Simplify |
| docs/webapp/pages/Export-Download.md | (merged into export-download.md) | Merge |
| docs/webapp/Portfolios.md | docs/user-guide/webapp/portfolios.md | Migrate + Verify |
| docs/plots/Bar-Charts.md | docs/user-guide/plots/bar-charts.md + grouped/stacked | Split + Verify |
| docs/plots/Line-Plots.md | docs/user-guide/plots/line-plots.md | Migrate + Verify |
| docs/plots/Scatter-Plots.md | docs/user-guide/plots/scatter-plots.md | Migrate + Verify |
| docs/plots/histogram-plot.md | docs/user-guide/plots/histogram-plot.md | Migrate + Fix refs |
| docs/plots/Grouped-Stacked-Bars.md | docs/user-guide/plots/grouped-stacked-bars.md | Migrate + Expand |
| docs/api/Data-Transformations.md | docs/user-guide/data-transformations/shaper-user-guide.md | Migrate + Simplify |

---

## 6. Content to Remove from User Guide

The following content from existing docs should NOT appear in the user guide (it belongs
in the developer guide):
- Internal file paths and module references
- Code examples with import statements
- Architecture diagrams and layer explanations
- Service method signatures
- Protocol definitions
- `.agent/` references

---

## 7. Writing Standards for User Guide

1. **Task-oriented** — Every page answers "how do I do X?"
2. **No code** — Users should never see Python code
3. **Screenshots welcome** — Reference UI elements visually when available
4. **Progressive complexity** — Start simple, add detail gradually
5. **Practical examples** — Use gem5 simulation scenarios as examples
6. **Cross-reference** — Link to related pages (plot type → settings → export)
7. **Troubleshooting** — Each page has a "Common Issues" section

---

## 8. Estimated Total Size

| Section | Files | Estimated Lines |
|---------|-------|-----------------|
| index.md | 1 | ~80 |
| getting-started/ | 3 | ~600 |
| webapp/ | 7 | ~2000 |
| plots/ | 9 | ~2500 |
| data-transformations/ | 1 | ~400 |
| **Total** | **21 files** | **~5,580 lines** |
