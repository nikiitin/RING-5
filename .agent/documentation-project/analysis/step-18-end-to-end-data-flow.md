# Step 18 — End-to-End Data Flow Analysis

> **Objective**: Trace the complete journey of data through the entire application —
> from raw simulator output files to rendered publication-quality plots. Show every
> transformation, model, service, and state change.

---

## Scope

This is a **cross-cutting synthesis step** that builds on ALL prior analysis steps. It
traces data through every layer and component, creating a complete data flow map.

---

## Prerequisites

This step requires completed analysis from:
- Step 01 (architecture) — layer boundaries
- Step 02 (models) — data types at each stage
- Step 03 (services) — service methods that transform data
- Step 04 (state) — where data is stored at each stage
- Step 05 (parsing) — data entry point
- Step 06 (shapers) — data transformation
- Step 07 (viz config) — configuration created from data
- Step 08 (pages) — UI triggers for data flow
- Step 10 (plotting) — plot creation from data
- Step 11 (rendering) — final data → visual translation
- Step 14 (export) — visual → file translation

---

## Data Flow Stages to Trace

### Stage 1: Raw Input → Parsed Data
```
Trace:
- raw gem5 stats.txt files on disk
  → ScannerService.scan()
    → pattern list (PatternAggregator)
      → user selects variables
        → ParseService.parse()
          → DataFrame (stored in DataRepository)

Document at each sub-step:
- Input type and shape
- Output type and shape
- Service method called
- State changes
- Models involved
```

### Stage 2: Parsed Data → Shaped Data
```
Trace:
- DataFrame from DataRepository
  → user configures shaper pipeline (UI)
    → ShaperFactory.create() per step
      → PipelineService.execute()
        → transformed DataFrame
          → stored where? (back to DataRepository? preview?)

Document at each sub-step:
- Input DataFrame columns/shape
- Shaper configuration model
- Output DataFrame columns/shape
- How pipeline composition works
```

### Stage 3: Shaped Data → Plot Configuration
```
Trace:
- transformed DataFrame
  → user selects plot type
    → PlotFactory creates plot instance
      → plot type declares data mapping
        → user configures settings (pills)
          → config builder collects settings
            → FigureConfig created

Document at each sub-step:
- How data columns map to trace roles (x, y, color, etc.)
- How settings are collected from UI state
- How FigureConfig is assembled
- All config sub-objects created
```

### Stage 4: Plot Configuration → Rendered Output
```
Trace:
- FigureConfig
  → EngineManager selects connector
    → Connector renders (Plotly or Matplotlib)
      → TraceBuildResult for each trace
        → Layout/axes/legend applied
          → RenderResult produced
            → ChartDisplay shows result

Document at each sub-step:
- How each config field maps to engine API calls
- Plotly vs Matplotlib divergence points
- Where engine-specific logic lives
```

### Stage 5: Rendered Output → Exported File
```
Trace:
- RenderResult
  → user selects export format
    → preset applied (if selected)
      → engine-specific export (savefig, to_image)
        → bytes generated
          → Streamlit download_button serves file

Document at each sub-step:
- Format-specific rendering paths
- Preset application
- Post-processing
```

### Stage 6: Session → Portfolio → Session (Round Trip)
```
Trace:
- all repositories
  → PortfolioService.save()
    → portfolio schema
      → JSON/file on disk
        → PortfolioService.load()
          → migration (if needed)
            → state restored to repositories
              → UI re-renders

Document at each sub-step:
- What is serialized from each repository
- What is the portfolio file format
- How migration transforms the schema
- How state restoration triggers UI refresh
```

---

## Questions to Answer

### Data Types at Each Stage:
- [ ] What is the exact data type at each transition point?
- [ ] Where do DataFrames live? (memory? session_state? disk?)
- [ ] How do DataFrame schemas change through the pipeline?
- [ ] Are there any data copies vs. references?

### Error Paths:
- [ ] What happens when parsing fails at each stage?
- [ ] What happens when shaping fails?
- [ ] What happens when rendering fails?
- [ ] How are user-facing errors generated?
- [ ] Is there error recovery at any stage?

### Performance Characteristics:
- [ ] What are the expensive operations in the pipeline?
- [ ] Where is caching applied?
- [ ] What is the typical data size at each stage?
- [ ] Are there any memory-sensitive transitions?

---

## Information to Extract

### Complete Data Flow Diagram
```
[ASCII art or structured text showing the complete flow]

Raw Files → Scanner → Patterns → Parser → DataFrame
    → Shapers (pipeline) → Shaped DataFrame
    → Plot Type + Settings → FigureConfig
    → Connector → Rendered Figure
    → Export → File Download

Parallel path:
    Session State ↔ Portfolio (save/load)
```

### State Transition Table
```
| Stage | Input | Output | Service | State Changed | Model |
|-------|-------|--------|---------|---------------|-------|
| Scan  | dir path | pattern list | ScannerService | ParserState | ScanResult |
| Parse | patterns | DataFrame | ParseService | DataRepo | DataFrame |
| Shape | DataFrame | DataFrame | PipelineService | DataRepo? | DataFrame |
| ...   | ...   | ...    | ...     | ...           | ...   |
```

---

## Output Template

### 1. Complete Data Flow Diagram
```
[To be filled]
```

### 2. Stage-by-Stage Documentation
```
[To be filled — one section per stage with full detail]
```

### 3. State Transition Table
```
[To be filled]
```

### 4. Error Path Documentation
```
[To be filled]
```

### 5. Performance Characteristics
```
[To be filled]
```

### 6. DataFrame Schema Evolution
```
[To be filled — how DataFrame columns/shape changes at each stage]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `architecture/data-flow.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/data-flow.md`
- Step 19 (extension points) — understanding the flow reveals where extensions plug in
