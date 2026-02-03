# RING-5 AI Agent Configuration

**Purpose**: AI assistant rules, workflows, and skills for RING-5 development.

## 🎯 Quick Start

### For Google Antigravity Users

- **Rules**: [rules/project-context.md](rules/project-context.md) - Always active
- **Workflows**: Invoke with `/workflow-name` (see [workflows/](workflows/))
- **Skills**: Auto-activate based on task (see [skills/](skills/))
- **Guide**: [ANTIGRAVITY_README.md](ANTIGRAVITY_README.md)

### For GitHub Copilot (VSCode) Users

- **Instructions**: [../.github/copilot-instructions.md](../.github/copilot-instructions.md)
- **Skills**: Available in [skills/\*.md](skills/) (legacy format)
- **Workflows**: Referenced as documentation patterns

### Dual IDE Support

See [DUAL_IDE_SETUP.md](DUAL_IDE_SETUP.md) for complete dual-IDE configuration guide.

---

## 📚 Directory Structure

```
.agent/
├── rules/                         # Constraints and guidelines
│   └── project-context.md        # Core project rules (12K char limit)
├── workflows/                     # Step-by-step processes
│   ├── test-driven-development.md
│   ├── new-variable-type.md
│   └── README.md                 # Workflow catalog
├── skills/                        # Reusable knowledge packages
│   ├── parsing-workflow/
│   │   └── SKILL.md              # Antigravity format (YAML frontmatter)
│   ├── new-plot-type/
│   │   └── SKILL.md
│   ├── shaper-pipeline/
│   │   └── SKILL.md
│   ├── debug-async-parsing/
│   │   └── SKILL.md
│   ├── *.md                      # Legacy format (Copilot compatible)
│   └── README.md                 # Skills catalog
├── ANTIGRAVITY_README.md          # Antigravity-specific guide
├── DUAL_IDE_SETUP.md              # Dual IDE configuration guide
└── README.md                      # This file
```

---

## 📖 Skills (Detailed How-To Guides)

Skills provide step-by-step instructions for implementing specific features.

### 1. [parsing-workflow.md](skills/parsing-workflow.md)

**Domain**: Data Ingestion
**Complexity**: Intermediate
**Purpose**: Complete gem5 stats parsing workflow

**Covers**:

- 4-phase workflow: Scanning → Selection → Parsing → Loading
- Async API usage patterns
- Error handling strategies
- Testing patterns with pytest
- Streamlit UI integration
- Performance optimization tips

**When to use**: Implementing new data sources, fixing parsing bugs, adding new variable support

---

### 2. [new-plot-type.md](skills/new-plot-type.md)

**Domain**: Visualization
**Complexity**: Intermediate
**Purpose**: Adding new plot types to the visualization system

**Covers**:

- Factory pattern implementation
- BasePlot interface
- Plotly figure creation
- UI configuration rendering
- Unit and integration testing
- Publication quality standards

**When to use**: Adding bar charts, line plots, heatmaps, or custom visualizations

---

### 3. [shaper-pipeline.md](skills/shaper-pipeline.md)

**Domain**: Data Transformation
**Complexity**: Intermediate
**Purpose**: Creating custom shapers and transformation pipelines

**Covers**:

- Shaper pattern and architecture
- Built-in shapers (rename, filter, aggregate, compute, normalize)
- Creating custom shapers
- Pipeline composition
- Immutability patterns
- Testing transformations

**When to use**: Data cleanup, normalization, aggregation, derived metrics

---

### 4. [debug-async-parsing.md](skills/debug-async-parsing.md)

**Domain**: Troubleshooting
**Complexity**: Intermediate
**Purpose**: Debugging async parsing and scanning issues

**Covers**:

- Future timeout errors
- Empty parse results
- Variable not found errors
- CSV merge failures
- Memory issues with large files
- Debug utilities and logging

**When to use**: Parse failures, timeout issues, debugging production problems

---

## Workflows (Process Automation)

Workflows define standardized processes for common development tasks.

### 1. [test-driven-development.md](workflows/test-driven-development.md)

**Complexity**: Fundamental
**Applies to**: All code changes
**Purpose**: TDD process for RING-5

**Covers**:

- Write test → Fail → Implement → Pass → Refactor cycle
- Test organization (unit, integration, e2e)
- Pytest fixtures and mocking patterns
- Coverage goals and standards
- Debugging failing tests

**When to use**: Every time you write new code or fix bugs

---

### 2. [new-variable-type.md](workflows/new-variable-type.md)

**Complexity**: Advanced
**Applies to**: gem5 parser extensions
**Purpose**: Adding support for new gem5 variable types

**Covers**:

- Creating Perl parser scripts
- Updating TypeMapper
- Scanner integration
- Complete testing workflow
- Documentation updates
- UI integration

**When to use**: gem5 adds new stat types, supporting custom simulator outputs

---

## Quick Selection Guide

### By Task Type

| Task                  | Use This                                                           |
| --------------------- | ------------------------------------------------------------------ |
| Parse new data source | [parsing-workflow.md](skills/parsing-workflow.md)                  |
| Add new chart type    | [new-plot-type.md](skills/new-plot-type.md)                        |
| Transform data        | [shaper-pipeline.md](skills/shaper-pipeline.md)                    |
| Fix parsing bugs      | [debug-async-parsing.md](skills/debug-async-parsing.md)            |
| Write new feature     | [test-driven-development.md](workflows/test-driven-development.md) |
| Support new gem5 type | [new-variable-type.md](workflows/new-variable-type.md)             |

### By Complexity

| Level            | Skills                                | Workflows         |
| ---------------- | ------------------------------------- | ----------------- |
| **Fundamental**  | -                                     | TDD               |
| **Intermediate** | Parsing, Plotting, Shapers, Debugging | -                 |
| **Advanced**     | -                                     | New Variable Type |

### By Domain

| Domain                | Guides                                |
| --------------------- | ------------------------------------- |
| **Data Ingestion**    | parsing-workflow, debug-async-parsing |
| **Visualization**     | new-plot-type                         |
| **Transformation**    | shaper-pipeline                       |
| **Parser Extension**  | new-variable-type                     |
| **Quality Assurance** | test-driven-development               |

## Common Workflows

### Adding a New Feature

1. Start with [test-driven-development.md](workflows/test-driven-development.md)
2. Choose domain-specific skill:
   - Data? → [parsing-workflow.md](skills/parsing-workflow.md)
   - Plot? → [new-plot-type.md](skills/new-plot-type.md)
   - Transform? → [shaper-pipeline.md](skills/shaper-pipeline.md)
3. If stuck, use [debug-async-parsing.md](skills/debug-async-parsing.md)

### Fixing a Bug

1. Reproduce with test ([test-driven-development.md](workflows/test-driven-development.md))
2. Debug using [debug-async-parsing.md](skills/debug-async-parsing.md)
3. Fix and verify tests pass

### Extending Parser

1. Follow [new-variable-type.md](workflows/new-variable-type.md)
2. Test with [parsing-workflow.md](skills/parsing-workflow.md) examples
3. Ensure TDD compliance ([test-driven-development.md](workflows/test-driven-development.md))

## Integration with AI Assistants

### GitHub Copilot (VS Code)

- Automatically reads `.github/copilot-instructions.md`
- Skills/workflows referenced in instructions
- Use inline comments to trigger skill usage:
  ```python
  # Following parsing-workflow.md: Step 1 - Scan
  scan_futures = facade.submit_scan_async(...)
  ```

### Cursor/Antigravity

- Reads `.cursorrules` on project open
- Skills/workflows listed in cursorrules
- Use chat commands:
  ```
  @skills parsing-workflow.md
  @workflows test-driven-development.md
  ```

### MCP-Compatible Assistants

- Access via `.mcp-config.json` servers
- Skills exposed through `ring5-skills` server
- Workflows through `ring5-workflows` server

## Maintenance

### Adding New Skills/Workflows

1. **Create the markdown file**:

   ```bash
   # For skills
   touch .agent/skills/my-new-skill.md

   # For workflows
   touch .agent/workflows/my-new-workflow.md
   ```

2. **Follow the template**:
   - Include: Purpose, Complexity, Domain
   - Add step-by-step instructions
   - Provide code examples
   - Add checklist
   - Reference related files

3. **Update this index**:
   - Add to appropriate section
   - Update quick selection guide
   - Add to common workflows if applicable

4. **Update AI configurations**:
   - Add to `.github/copilot-instructions.md`
   - Add to `.cursorrules`
   - Update `.ai-assistant-guide.md`

### Deprecating Skills/Workflows

1. Mark as deprecated in header:

   ```markdown
   **Status**: DEPRECATED - Use [new-skill.md](new-skill.md) instead
   ```

2. Update this index
3. Update AI configurations
4. Keep file for 2 releases before removing

## Contributing

When creating new skills/workflows:

- **Be specific**: Focus on one task or process
- **Be practical**: Include real code examples
- **Be testable**: Provide verification steps
- **Be current**: Keep in sync with codebase changes
- **Be linked**: Reference actual implementation files

## References

- Full project rules: `.agent/rules/project-context.md`
- Quick start: `QUICKSTART.md`
- Setup guide: `AI-SETUP.md`
- Architecture docs: `src/` module docstrings
