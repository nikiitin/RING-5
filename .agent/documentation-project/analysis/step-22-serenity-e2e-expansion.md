# Step 22 — Serenity BDD, Reporting Tools & E2E Toolchain Investigation

> **Objective**: Research Serenity BDD, Allure, and other reporting/living-documentation
> tools. Decide what to adopt. Evaluate how to maximize the value of our E2E tests as
> both regression tests AND documentation generators.

---

## Scope

Our E2E tests serve a dual purpose:
1. **Regression testing** — verify the UI works correctly
2. **Documentation generation** — produce screenshots, GIFs, and reports for user guides

We need tooling that maximizes both. This step evaluates options.

---

## Tools to Research

### Serenity BDD / Serenity JS
```
- What: BDD framework that generates "living documentation" reports
- Website: serenity-bdd.github.io / serenity-js.org
- Key feature: Rich HTML reports with screenshots at each step
- Question: Does it work with Python/pytest-playwright?
```

### Allure Framework
```
- What: Test report framework with Python-native support
- Website: allurereport.org
- Key feature: pytest-allure plugin, screenshots, steps, attachments
- Question: How does it compare to Serenity for our use case?
```

### Playwright Built-in Reporting
```
- What: Playwright's native HTML reporter and trace viewer
- Documentation: playwright.dev/docs/test-reporters
- Key feature: Step-by-step screenshots, video, trace
- Question: Can we extract documentation media from Playwright traces?
```

### Custom Report Generator
```
- What: Build our own from test artifacts (screenshots, metadata)
- Key feature: Full control, no external dependencies
- Question: Worth the engineering cost?
```

### pytest-html
```
- What: Simple HTML report plugin for pytest
- Key feature: Screenshot attachments, minimal setup
- Question: Too basic for our needs?
```

---

## Research Questions

### Serenity BDD Deep Dive:
- [ ] What is the Screenplay Pattern? Is it compatible with our POM pattern?
- [ ] Does Serenity JS's `@serenity-js/playwright` work with Python tests?
- [ ] Can Serenity consume pytest-playwright output (e.g., via JUnit XML)?
- [ ] Can Serenity generate reports from test artifacts without running tests itself?
- [ ] What does a Serenity report look like? (get examples)
- [ ] What is the Serenity report generation build step?
- [ ] Does Serenity support GIF generation from step screenshots?
- [ ] Can Serenity automatically annotate screenshots with step descriptions?
- [ ] Is there a Serenity Python binding? (serenity-python?)

### Allure Deep Dive:
- [ ] How does allure-pytest integrate with pytest-playwright?
- [ ] Can Allure attach screenshots at each test step?
- [ ] Can Allure generate "living documentation" similar to Serenity?
- [ ] What does an Allure report look like for visual tests?
- [ ] Can Allure produce individual media assets (not just reports)?
- [ ] Does Allure support GIF/video attachments?
- [ ] allure-pytest installation and configuration effort?

### Playwright Reporting:
- [ ] Can we use Playwright's HTML reporter with pytest-playwright?
- [ ] Can we extract individual screenshots from Playwright traces?
- [ ] Can we convert Playwright trace files to documentation media?
- [ ] What is the trace viewer's capability for step-by-step documentation?

### Dual-Purpose Test Design:
- [ ] How to annotate tests as "documentation generators" vs "regression only"?
- [ ] How to mark specific screenshots as "publish to docs" vs "internal only"?
- [ ] Can test metadata (descriptions, step labels) feed into report/docs?
- [ ] How to version media assets alongside test code?

---

## Evaluation Matrix

```
| Criterion | Serenity BDD | Allure | Playwright | Custom | pytest-html |
|-----------|-------------|--------|------------|--------|-------------|
| Python native | ? | YES | Partial | YES | YES |
| pytest integration | ? | Excellent | Good | N/A | Good |
| Step screenshots | YES | YES | YES (trace) | Manual | Basic |
| Living documentation | Excellent | Good | No | Manual | No |
| GIF generation | ? | No | No | Manual | No |
| Report quality | Excellent | Excellent | Good | Variable | Basic |
| Setup effort | HIGH? | MEDIUM | LOW | HIGH | LOW |
| Maintenance cost | ? | LOW | LOW | MEDIUM | LOW |
| Media extraction | ? | YES | Trace-based | YES | No |
| CI integration | ? | YES | YES | YES | YES |
```

---

## Decision Framework

```
Recommendation criteria (weighted):

1. (Must-have) Works with Python pytest-playwright
2. (Must-have) Can attach screenshots per test step
3. (High) Generates documentation-quality reports
4. (High) Individual media assets extractable (not just in report)
5. (Medium) Step descriptions visible in output
6. (Medium) Setup effort < 1 day
7. (Low) GIF generation built-in
8. (Low) BDD syntax support
```

---

## Output Template

### 1. Serenity BDD Assessment
```
[To be filled: Verdict, rationale, integration feasibility]
```

### 2. Allure Framework Assessment
```
[To be filled: Verdict, rationale, integration plan]
```

### 3. Playwright Reporting Assessment
```
[To be filled: Verdict, capabilities, limitations]
```

### 4. Tool Comparison Matrix (filled)
```
[To be filled]
```

### 5. Final Recommendation
```
[To be filled: Which tool(s) to adopt, integration plan, timeline]
```

### 6. Hybrid Approach Design
```
[To be filled: How to combine tools if needed
  e.g., Allure for reports + custom script for GIF generation]
```

---

## Downstream Dependencies

This step feeds into:
- Steps 23-30 (all E2E test steps) — determines tooling for test annotations and reporting
- Phase B0 (media generation) — determines how media is extracted from tests
- `DEVELOPER_GUIDE_PLAN.md` → `testing/e2e-playwright-testing.md`
