# Step 30 — E2E Tests: Portfolio, Cross-Page Workflows & Documentation Media Assembly

> **Objective**: Design E2E tests for portfolio save/load, complete cross-page workflows,
> error handling, and the final media assembly step that ensures ALL 74+ documentation
> media assets are generated and organized.

---

## Scope

This is the **capstone E2E step** covering:
1. Portfolio save/load round-trip tests
2. Cross-page workflow tests (complete user journeys)
3. Error handling across the application
4. Navigation and page transition tests
5. Final media assembly and validation

---

## Part 1: Portfolio Tests

### Files to Analyze
```
src/web/pages/portfolio.py
src/core/services/data_services/portfolio_service.py
src/core/services/portfolio_migrator.py
src/core/models/portfolio_models.py
tests/visual/pages/portfolio_page.py                 (existing — 68 lines, minimal)
```

### Tests to Design
- [ ] Save empty session (no data) → verify error/warning
- [ ] Save after parse → verify portfolio created
- [ ] Save after parse + plot configured → verify full state saved
- [ ] Load portfolio → verify all state restored (data, plots, settings)
- [ ] Load portfolio → verify chart renders identically
- [ ] Portfolio overwrite → verify confirmation dialog
- [ ] Portfolio rename → verify name changes
- [ ] Portfolio delete → verify removal
- [ ] Load portfolio from older version → verify migration

### Documentation Media
```
Screenshots:
  portfolio-page.png
  portfolio-management.png

GIFs:
  save-workflow.gif
  load-workflow.gif
```

---

## Part 2: Cross-Page Workflow Tests

### Complete User Journey Tests
These test the FULL application workflow across multiple pages:

#### Journey 1: First-Time User
```
1. Open app → Data Source page
2. Fill paths → Scan → Add variables → Parse
3. Navigate to Data Managers → Reduce seeds
4. Navigate to Manage Plots → Create bar chart
5. Configure settings (title, labels, colors)
6. Switch to Matplotlib → Export as PDF
7. Save portfolio
→ This produces: full-app-workflow.gif
```

#### Journey 2: Returning User
```
1. Open app → Portfolio page
2. Load saved portfolio
3. Verify data and plots restored
4. Modify plot settings
5. Create additional plot (line)
6. Re-save portfolio
```

#### Journey 3: CSV User
```
1. Open app → Data Source → CSV mode
2. Upload CSV file
3. Navigate to Manage Plots → Create scatter plot
4. Configure and export
```

#### Journey 4: Multi-Plot Session
```
1. Parse data → Create bar chart
2. Create line chart (second plot)
3. Create scatter chart (third plot)
4. Switch between plots → verify state preserved
5. Configure each differently
6. Export all three
```

---

## Part 3: Error Handling Tests

### Error Scenarios Across Pages
- [ ] Data Source: invalid path → error displayed, no crash
- [ ] Data Source: permission denied → appropriate error
- [ ] Data Managers: operation on empty data → warning
- [ ] Manage Plots: create plot with no data → error/redirect
- [ ] Manage Plots: render with invalid config → graceful fallback
- [ ] Portfolio: load corrupted file → error message
- [ ] Portfolio: load file from incompatible version → migration or error
- [ ] Navigation: jump to Plot page without data → handled gracefully

---

## Part 4: Navigation Tests

### Page Transition Tests
- [ ] Navigate to each page via sidebar → verify correct page loads
- [ ] Navigate forward and back → verify state preservation
- [ ] Verify sidebar shows current page highlighted
- [ ] Verify page titles are correct

### Documentation Media
```
Screenshots:
  sidebar-navigation.png

GIFs:
  page-transitions.gif (navigate through all pages)
```

---

## Part 5: Documentation Media Assembly

### Media Validation Checklist
After ALL steps 23-30 are executed, validate that every asset in the manifest exists:

```
docs/user-guide/media/
├── getting-started/       (4 assets)    ✓/✗
├── data-source/           (12 assets)   ✓/✗
├── data-managers/         (10 assets)   ✓/✗
├── manage-plots/          (21 assets)   ✓/✗
├── plots/                 (14 assets)   ✓/✗
├── export/                (5 assets)    ✓/✗
├── portfolio/             (5 assets)    ✓/✗
└── navigation/            (3 assets)    ✓/✗
                           ──────────
                           74 total
```

### Media Quality Checks
- [ ] All screenshots have consistent resolution (1280×800 @2x)
- [ ] All screenshots use dark theme
- [ ] All screenshots have en-US locale
- [ ] All GIFs have reasonable file size (< 500KB)
- [ ] All GIFs have adequate frame rate (2-4 fps)
- [ ] All GIFs show complete workflow (no cut-off steps)
- [ ] No PII or sensitive paths visible in screenshots
- [ ] Test data shows recognizable but non-proprietary results

### Media Regeneration Command
```bash
# Single command to regenerate ALL documentation media
pytest tests/visual/docs_media/ -m requires_browser --no-cov -p no:xdist -v
```

### POM Additions for Portfolio
- [ ] Save dialog locators
- [ ] Load dialog/browser locators
- [ ] Portfolio list locators
- [ ] Rename/delete action locators
- [ ] Confirmation dialog locators
- [ ] File management locators

---

## Output Template

### 1. Portfolio Test Specifications
```
[To be filled]
```

### 2. Cross-Page Journey Tests
```
[To be filled]
```

### 3. Error Handling Tests
```
[To be filled]
```

### 4. Navigation Tests
```
[To be filled]
```

### 5. POM Additions (Portfolio + cross-page)
```
[To be filled]
```

### 6. Media Assembly Validation Checklist
```
[To be filled]
```

### 7. Complete Media Asset Manifest (final, all 74 assets)
```
[To be filled: the definitive manifest with test → asset mapping]
```

---

## Downstream Dependencies

- Uses Tier 1 and Tier 2 snapshots
- Portfolio tests validate the snapshot save/restore mechanism itself
- Media assembly step validates ALL prior E2E steps produced their assets
- This is the FINAL E2E step — after this, Phase B0 media generation is complete
