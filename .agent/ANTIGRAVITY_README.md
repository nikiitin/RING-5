# Google Antigravity IDE Configuration

This directory contains configurations for both **GitHub Copilot** (VSCode) and **Google Antigravity** IDE.

## Structure

```
.agent/
├── rules/                    # Rules (constraints/guidance for agents)
│   └── project-context.md   # Main project rules (works in both IDEs)
├── workflows/                # Workflows (step-by-step processes)
│   ├── *.md                 # Workflow files (Antigravity format)
│   └── README.md            # Workflow catalog
├── skills/                   # Skills (reusable knowledge packages)
│   ├── */SKILL.md           # Antigravity format (YAML frontmatter)
│   └── *.md                 # Legacy format (GitHub Copilot compatible)
└── ANTIGRAVITY_README.md    # This file
```

## For Google Antigravity Users

### Rules
- **Location**: `.agent/rules/`
- **Format**: Markdown files (12,000 char limit each)
- **Activation**: Manual (@mention), Always On, Model Decision, or Glob pattern
- **Main Rule**: `project-context.md` - Core project guidelines

### Workflows
- **Location**: `.agent/workflows/`
- **Format**: Markdown with title, description, and steps
- **Invocation**: `/workflow-name` in Agent input
- **Available Workflows**:
  - `/test-driven-development` - TDD process for all code changes
  - `/new-variable-type` - Adding support for new gem5 variable types

### Skills
- **Location**: `.agent/skills/<skill-name>/SKILL.md`
- **Format**: Markdown with YAML frontmatter
- **Activation**: Automatic based on description relevance
- **Available Skills**:
  - `parsing-workflow` - gem5 statistics parsing workflows
  - `new-plot-type` - Adding new visualization types
  - `shaper-pipeline` - Data transformation pipelines
  - `debug-async-parsing` - Debugging async parsing issues

## For GitHub Copilot Users

All configurations in `.github/copilot-instructions.md` work seamlessly.
Legacy skill files (`.agent/skills/*.md`) are also compatible.

## Dual IDE Support

Both IDE configurations point to the same:
- Project structure
- Code conventions
- Testing patterns
- Architecture principles

This ensures consistent AI behavior regardless of IDE choice.
