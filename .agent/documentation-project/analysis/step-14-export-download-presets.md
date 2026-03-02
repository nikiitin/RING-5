# Step 14 — Export, Download & Presets System Analysis

> **Objective**: Document the complete export/download system — format support, presets,
> venue-specific configurations, download UI, and the rendering-to-file pipeline.

---

## Scope

This step analyzes how plots are **exported to publication-quality files** — the available
formats, preset configurations, and the download workflow.

---

## Files to Analyze

### Download UI
```
src/web/pages/ui/plotting/download_section.py      (download UI component)
```

### Export System
```
src/web/pages/ui/plotting/export/__init__.py
src/web/pages/ui/plotting/export/presets/__init__.py
src/web/pages/ui/plotting/export/presets/preset_manager.py
src/web/pages/ui/plotting/export/presets/preset_schema.py
```

### Preset Applicator
```
src/web/rendering/preset_applicator.py             (applies presets to config)
```

### Rendering (export paths)
```
src/web/rendering/engine_manager.py                (engine selection for export)
src/web/rendering/plotly_connector.py              (Plotly export methods)
src/web/rendering/matplotlib_connector.py          (Matplotlib export methods)
```

### Related Visualization Best Practices
```
.agent/context/visualization-best-practices.md     (venue-specific standards)
```

---

## Questions to Answer

### Export Formats:
- [ ] What file formats are supported? (PNG, SVG, PDF, PGF, HTML, etc.)
- [ ] Which formats are supported by which engine?
- [ ] What are the default export settings? (DPI, size, etc.)
- [ ] How are format-specific options configured?
- [ ] Is there a quality/size trade-off configuration?

### Download Section UI:
- [ ] What download options are presented to the user?
- [ ] How does the user select format, size, DPI?
- [ ] Can the user preview before download?
- [ ] What is the download trigger mechanism? (Streamlit download button?)
- [ ] How are large file exports handled?

### Presets:
- [ ] What is a preset? (schema definition)
- [ ] What built-in presets exist?
- [ ] What venue-specific presets exist? (IEEE, ISCA/MICRO, Nature, Science, etc.)
- [ ] What does each preset configure? (size, DPI, fonts, margins)
- [ ] How is a preset applied? (mutates FigureConfig? creates new one?)
- [ ] Can users create custom presets?
- [ ] Where are presets stored? (in-code? JSON? YAML?)

### Preset Manager:
- [ ] How does the preset manager work?
- [ ] How are presets loaded and registered?
- [ ] How are presets applied to a plot?
- [ ] What is the preset application order? (preset → user overrides?)

### Export Pipeline:
- [ ] What is the step-by-step export flow?
- [ ] How does the rendered figure become a downloadable file?
- [ ] How are image bytes generated? (kaleido? agg backend? savefig?)
- [ ] What post-processing occurs? (font embedding? compression?)
- [ ] How are LaTeX-compatible exports generated?

---

## Information to Extract

### Format Support Matrix
```
| Format | Plotly | Matplotlib | Notes |
|--------|--------|------------|-------|
| PNG    | Yes    | Yes        | Via kaleido / agg backend |
| SVG    | Yes    | Yes        | ... |
| PDF    | ?      | Yes        | ... |
| PGF    | No     | Yes        | LaTeX native |
| HTML   | Yes    | No         | Interactive |
| ...    | ...    | ...        | ... |
```

### Preset Catalog
```
For each preset:
- Name
- Target venue/use case
- Dimensions (width × height)
- DPI
- Font family and sizes
- Margin/padding
- Color scheme
```

### Export Pipeline Flow
```
1. User clicks download button
2. Export settings collected (format, preset, custom overrides)
3. Preset applied to FigureConfig (if selected)
4. FigureConfig rendered by appropriate engine
5. Output bytes generated (format-specific)
6. File served to browser for download
```

---

## Output Template

### 1. Format Support Documentation
```
[To be filled]
```

### 2. Download Section UI Documentation
```
[To be filled]
```

### 3. Preset Schema Documentation
```
[To be filled]
```

### 4. Preset Catalog
```
[To be filled]
```

### 5. Preset Manager Documentation
```
[To be filled]
```

### 6. Preset Applicator Documentation
```
[To be filled]
```

### 7. Export Pipeline Flow
```
[To be filled]
```

### 8. LaTeX Integration Documentation
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `export/export-system.md`, `export/adding-export-format.md`
- `USER_GUIDE_PLAN.md` → `webapp/export-download.md`
- Step 18 (data flow) — export is the final output step
- Step 19 (extension points) — preset system as an extension point
