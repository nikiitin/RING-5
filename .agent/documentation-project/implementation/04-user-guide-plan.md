# User Guide Implementation Plan

> Source analysis: Steps 08-15 (pages, components, plotting, rendering, settings,
> controllers, export, portfolio).

---

## 1. Output Structure

```
docs/user-guide/
├── index.md                        # Welcome + quick start
├── getting-started/
│   ├── installation.md             # How to install and run RING-5
│   ├── first-steps.md              # Loading data and creating first plot
│   └── concepts.md                 # Key concepts (simulator, variables, shapers)
├── pages/
│   ├── data-source.md              # Data Source page guide
│   ├── data-managers.md            # Data Managers page guide
│   ├── manage-plots.md             # Manage Plots page guide
│   ├── portfolio.md                # Portfolio page guide
│   └── documentation.md            # In-app documentation
├── tutorials/
│   ├── load-and-explore.md         # Load CSV, explore data
│   ├── create-bar-chart.md         # Step-by-step bar chart
│   ├── normalize-data.md           # Shaper pipeline for normalization
│   ├── publication-ready.md        # Export for IEEE/ACM paper
│   ├── compare-simulations.md      # Multi-seed analysis
│   └── custom-styling.md           # Advanced typography/legend/colors
├── features/
│   ├── plot-types.md               # All 9 plot types with examples
│   ├── shapers.md                  # All 10 shaper types explained
│   ├── settings.md                 # Settings pills overview
│   ├── export-presets.md           # 13 presets for different venues
│   ├── dual-engine.md              # Plotly vs Matplotlib
│   └── portfolios.md               # Save/load workspace snapshots
└── reference/
    ├── keyboard-shortcuts.md       # If any
    ├── supported-formats.md        # CSV, stats.txt, export formats
    └── faq.md                      # Common questions
```

---

## 2. Writing Plan Per Section

### Getting Started (from Steps 08, 17)

| File | Content | Est. Lines |
|------|---------|------------|
| `installation.md` | Python 3.11+, pip install, streamlit run | 100 |
| `first-steps.md` | Load sample CSV → Create bar plot → Export PNG | 200 |
| `concepts.md` | Simulator, variables, entries, shapers, pipeline, presets | 150 |

### Page Guides (from Steps 08, 09)

| File | Source | Content | Est. Lines |
|------|--------|---------|------------|
| `data-source.md` | Step 08, 09 | CSV pool, scanning, parsing, variable editor | 300 |
| `data-managers.md` | Step 08, 09 | Preprocessor, seeds reducer, outlier remover, mixer | 250 |
| `manage-plots.md` | Step 08, 10 | Plot creation, settings, shaper pipeline, download | 400 |
| `portfolio.md` | Step 08, 15 | Save, load, delete, portfolio list | 200 |

### Tutorials (from Steps 06, 10, 11, 12, 14)

| File | Content | Est. Lines |
|------|---------|------------|
| `load-and-explore.md` | End-to-end: scan → parse → load → preview | 250 |
| `create-bar-chart.md` | Select columns → Create plot → Customize | 200 |
| `normalize-data.md` | Column selector → Normalize → Compare | 200 |
| `publication-ready.md` | Create plot → Apply ISCA preset → Export PDF | 250 |
| `compare-simulations.md` | Load multi-seed → Seeds reducer → Grouped bar | 200 |
| `custom-styling.md` | Typography → Colors → Legend → Reference lines | 250 |

### Features (from Steps 06, 10, 11, 12, 14)

| File | Source | Content | Est. Lines |
|------|--------|---------|------------|
| `plot-types.md` | Step 10 | 9 types with use cases and column requirements | 350 |
| `shapers.md` | Step 06 | 10 types with parameter descriptions | 300 |
| `settings.md` | Step 12 | 11 pills with available options | 250 |
| `export-presets.md` | Step 14 | 13 presets with dimensions/venue info | 200 |
| `dual-engine.md` | Step 11 | When to use Plotly vs Matplotlib | 150 |
| `portfolios.md` | Step 15 | How portfolios preserve workspace state | 150 |

---

## 3. Estimated Totals

| Section | Files | Est. Lines |
|---------|-------|------------|
| Getting Started | 3 | 450 |
| Page Guides | 5 | 1,150 |
| Tutorials | 6 | 1,350 |
| Features | 6 | 1,400 |
| Reference | 3 | 300 |
| **Total** | **23 files** | **~4,650 lines** |

---

## 4. Implementation Order

1. **Getting Started** — First thing users need
2. **Page Guides** — Primary reference
3. **Features** — Plot types and shapers overview
4. **Tutorials** — Guided workflows
5. **Reference** — FAQ and formats

---

## 5. Screenshot Strategy

Each page guide and tutorial should include annotated screenshots:
- Use Playwright to capture consistent screenshots
- Annotate with numbered callouts (e.g., "1. Click here to load CSV")
- Store in `docs/user-guide/assets/`
- Regenerate screenshots automatically when UI changes

---

## 6. Style Guidelines

- Write for researchers who use gem5 but may not be Python developers
- Use second-person ("You can...") not third-person ("The user can...")
- Include expected outcomes after each step ("You should see a bar chart...")
- Show actual data values from the sample dataset
- Keep paragraphs short (2-3 sentences max)

---

## 7. Implementation Log

### Design Decisions (vs. original plan)

1. **No screenshots yet**: Screenshots deferred — text-only guides first; Playwright screenshot generation can be added later when UI stabilizes.
2. **24 files instead of 23**: Added `documentation.md` (57 lines) for the in-app Documentation page, which was in the file tree but not counted in the original estimate.
3. **All sections written in parallel**: 14 agents ran concurrently across 3 batches to maximize throughput.
4. **Style consistency**: All files follow second-person voice, include "You should see..." expected outcomes, use short paragraphs, and reference the sample CSV fixture data.

### Files Written

| File | Lines | Section |
|------|-------|---------|
| `index.md` | 48 | Landing page with Quick Start |
| `getting-started/installation.md` | 100 | Prerequisites, venv, pip install, streamlit run |
| `getting-started/concepts.md` | 93 | 9 key concepts explained |
| `getting-started/first-steps.md` | 262 | 7-step walkthrough |
| `pages/data-source.md` | 314 | Parse mode, CSV mode, Recent mode |
| `pages/data-managers.md` | 335 | 7 tabs: Summary through History |
| `pages/manage-plots.md` | 608 | Plot creation, config, pipeline, settings, export |
| `pages/portfolio.md` | 207 | Save/load/delete workflow |
| `pages/documentation.md` | 57 | In-app documentation reference |
| `features/plot-types.md` | 358 | 9 plot types with column requirements |
| `features/shapers.md` | 300 | 10 shaper types with parameters |
| `features/settings.md` | 347 | 11 settings pills detailed |
| `features/export-presets.md` | 338 | 13 presets with dimensions/venue info |
| `features/dual-engine.md` | 136 | Plotly vs Matplotlib comparison |
| `features/portfolios.md` | 164 | Portfolio system explained |
| `tutorials/load-and-explore.md` | 337 | CSV and gem5 stats loading + data inspection |
| `tutorials/create-bar-chart.md` | 199 | Step-by-step bar chart creation |
| `tutorials/normalize-data.md` | 243 | Shaper pipeline normalization workflow |
| `tutorials/publication-ready.md` | 367 | ISCA preset → PDF/PGF export for LaTeX |
| `tutorials/compare-simulations.md` | 327 | Multi-seed analysis with grouped bars |
| `tutorials/custom-styling.md` | 243 | Typography, colors, legends, axes, reference lines |
| `reference/supported-formats.md` | 102 | Input/export format reference |
| `reference/keyboard-shortcuts.md` | 65 | Streamlit + Plotly shortcuts |
| `reference/faq.md` | 110 | 10 common questions |
| **Total** | **5,660** | **24 files** |

### Actual vs. Estimated

| Section | Files | Est. Lines | Actual Lines |
|---------|-------|------------|-------------|
| Getting Started | 3 | 450 | 455 |
| Page Guides | 5 | 1,150 | 1,521 |
| Tutorials | 6 | 1,350 | 1,716 |
| Features | 6 | 1,400 | 1,643 |
| Reference | 3 | 300 | 277 |
| Index | 1 | — | 48 |
| **Total** | **24 files** | **~4,650** | **5,660** |

### Status: COMPLETE
