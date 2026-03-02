# Step 20 — Existing Documentation Audit

> **Objective**: Audit every existing documentation file against the current codebase.
> Identify outdated content, missing coverage, broken references, incorrect code examples,
> and deprecated features still documented.

---

## Scope

This step **compares existing documentation to reality**. Every claim in every doc file
is verified against the current source code.

---

## Files to Audit

### Root Documentation
```
docs/Home.md
docs/README.md
docs/index.md
docs/Installation.md
docs/_Sidebar.md
docs/_config.yml
```

### API Documentation
```
docs/api/Backend-Facade.md
docs/api/Data-Transformations.md
docs/api/Parsing-API.md
docs/api/Parsing-Guide.md
docs/api/Plotting-API.md
docs/api/Shaper-API.md
```

### Plot Documentation
```
docs/plots/Bar-Charts.md
docs/plots/Grouped-Stacked-Bars.md
docs/plots/histogram-plot.md
docs/plots/Line-Plots.md
docs/plots/Scatter-Plots.md
```

### Web App Documentation
```
docs/webapp/Creating-Plots.md
docs/webapp/Download-Guide.md
docs/webapp/First-Analysis.md
docs/webapp/Portfolios.md
docs/webapp/Quick-Start.md
docs/webapp/Web-Interface.md
docs/webapp/pages/Data-Source.md
docs/webapp/pages/Data-Managers.md
docs/webapp/pages/Manage-Plots.md
docs/webapp/pages/Plot-Settings.md
docs/webapp/pages/Export-Download.md
```

### Developer Documentation
```
docs/developer/Architecture.md
docs/developer/                                    (any other files)
```

### Root Files
```
README.md
CONTRIBUTING.md
```

### Agent Documentation (for cross-reference)
```
.agent/ARCHITECTURE.md
.agent/unified_architecture_manifesto.md
.agent/QUICKSTART.md
.agent/README.md
.github/copilot-instructions.md
```

---

## Audit Procedure for Each File

For every documentation file, check:

### 1. Accuracy
- [ ] Are all class/function names correct? (verify against source)
- [ ] Are all method signatures correct? (parameters, return types)
- [ ] Are all code examples valid? (would they run?)
- [ ] Are all file paths correct? (do referenced files exist?)
- [ ] Are all import statements correct?
- [ ] Are architectural claims correct? (layer boundaries, patterns)

### 2. Completeness
- [ ] Are all public APIs documented?
- [ ] Are all plot types documented?
- [ ] Are all shaper types documented?
- [ ] Are all settings documented?
- [ ] Are all pages documented?
- [ ] Are all components documented?

### 3. Currency
- [ ] Does it reference removed features? (Performance page, Presenters, etc.)
- [ ] Does it reference renamed classes/methods?
- [ ] Does it reference old import paths?
- [ ] Does it reference old dependencies? (PyYAML → stdlib json)
- [ ] Does it reflect the current UI pattern? (pills, not expanders)
- [ ] Does the test count match? (CONTRIBUTING.md says 653, reality is 3000+)

### 4. Internal Consistency
- [ ] Do different docs agree with each other?
- [ ] Are cross-references between docs correct?
- [ ] Do image references point to existing files?
- [ ] Are sidebar links all valid?

---

## Known Issues to Verify (From Prior Analysis)

### Already Identified Issues:
1. **Performance page references** — still in Web-Interface.md but feature was removed
2. **PyYAML dependency** — removed but still in Installation.md
3. **Test count** — CONTRIBUTING.md says 653, actual is 3000+
4. **Presenter pattern references** — presenters were deleted in current branch
5. **Markdown formatting** — Plotting-API.md line 261 has malformed code blocks
6. **Missing images** — some docs reference images that may not exist
7. **Internal path references** — histogram-plot.md references .agent/skills/
8. **index.md references** — references Architecture-Diagram.md which may not exist

### Issues to Discover:
- [ ] Any other outdated API references
- [ ] Any other removed feature references
- [ ] Any other broken cross-references
- [ ] Any other incorrect code examples
- [ ] Any coverage gaps (features without docs)

---

## Audit Output Format

For each file, produce:

```
### docs/xxx/Yyy.md

**Overall Status**: UP-TO-DATE / PARTIALLY OUTDATED / SIGNIFICANTLY OUTDATED

**Issues Found**:
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 15   | References removed Performance page | HIGH | Remove section |
| 42   | Method signature changed | MEDIUM | Update signature |
| ...  | ...   | ...      | ... |

**Missing Coverage**:
- [ ] Feature X not documented
- [ ] Method Y not documented

**Migration Plan**:
- Move to: docs/user-guide/xxx.md or docs/developer-guide/xxx.md
- Updates needed before migration: [list]
```

---

## Output Template

### 1. Audit Summary Matrix
```
[To be filled: File × Status × Issue Count × Migration Target]
```

### 2. Per-File Audit Reports
```
[To be filled: Detailed audit for each file]
```

### 3. List of All Outdated References
```
[To be filled]
```

### 4. List of Missing Documentation
```
[To be filled: Features/APIs with no documentation]
```

### 5. Migration Plan
```
[To be filled: Where each existing file should move in the new hierarchy]
```

### 6. Priority Fix List
```
[To be filled: Ordered list of fixes by severity]
```

---

## Downstream Dependencies

This analysis feeds into:
- Phase C of the MASTER_PLAN (existing docs audit & migration)
- `USER_GUIDE_PLAN.md` — determines what content can be reused
- `DEVELOPER_GUIDE_PLAN.md` — determines what developer content needs rewriting
- All documentation generation uses audit findings to avoid repeating known errors
