# Step 29 — E2E Tests: Export, Download & Presets (13 Presets × Formats × Engines)

> **Objective**: Design E2E tests for the complete export/download system — all formats,
> all 13 venue presets, download workflow, and preset effect verification.

---

## Scope

### Combinatorial Surface
```
Export formats (estimated 4-5): PNG, SVG, PDF, PGF, HTML
× 2 engines
× 13 presets + "no preset"
= ~130-180 combinations

Key scenarios:
  - Download in each format
  - Apply each preset → verify dimensions/fonts change
  - Preset + engine compatibility
  - Download file validity
```

---

## Files to Analyze
```
src/web/pages/ui/plotting/download_section.py
src/web/pages/ui/plotting/export/presets/preset_manager.py
src/web/pages/ui/plotting/export/presets/preset_schema.py
src/web/pages/ui/plotting/export/presets/latex_presets.json
src/web/rendering/preset_applicator.py

tests/visual/pages/manage_plots_page.py              (download section)
```

---

## Tests to Design

### Format Download Tests (using Tier 2 bar snapshot)
- [ ] Download as PNG → verify file downloads, non-empty
- [ ] Download as SVG → verify file downloads, valid SVG
- [ ] Download as PDF → verify file downloads (Matplotlib)
- [ ] Download as PGF → verify file downloads (Matplotlib)
- [ ] Download as HTML → verify file downloads (Plotly)
- [ ] Verify format availability per engine

### Preset Application Tests
For a representative subset of the 13 presets:
- [ ] Apply "single_column" → verify dimensions change
- [ ] Apply "ieee_single" → verify font/size change
- [ ] Apply "nature" → verify specific Nature formatting
- [ ] Apply "poster" → verify large dimensions
- [ ] Apply "slides" → verify slide-friendly dimensions
- [ ] Remove preset → verify defaults restored
- [ ] Preset + different plot types (at least bar, line, scatter)

### Download Workflow Tests
- [ ] Open download section → verify UI elements
- [ ] Select format → verify format pills/options
- [ ] Select preset → verify dropdown
- [ ] Click download → verify file served
- [ ] Multiple sequential downloads
- [ ] Download with modified settings (non-default)

### Documentation Media
```
Screenshots:
  download-section.png
  format-selection.png
  preset-selection.png
  publication-preset-comparison.png (same chart, different presets)

GIFs:
  download-workflow.gif (select format → select preset → download)
```

### POM Additions Needed
- [ ] Download section locators
- [ ] Format selection locators (pills? radio?)
- [ ] Preset dropdown/selection locator
- [ ] Download button locator
- [ ] Download event capture (Playwright download handler)
- [ ] Downloaded file validation helpers

---

## Output Template

### 1. Format × Engine Matrix
```
[To be filled: which formats work with which engine]
```

### 2. Preset Test Specifications
```
[To be filled]
```

### 3. Download Workflow Tests
```
[To be filled]
```

### 4. POM Additions
```
[To be filled]
```

### 5. Media Asset Manifest
```
[To be filled]
```

---

## Downstream Dependencies

- Uses Tier 2 snapshots from Step 25
- Media feeds into USER_GUIDE_PLAN → export-download.md
