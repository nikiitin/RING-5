# Dual IDE AI Configuration Summary

RING-5 supports **both Google Antigravity IDE and GitHub Copilot (VSCode)** with consistent AI agent behavior across both environments.

## 📋 Quick Reference

| Feature        | Google Antigravity                         | GitHub Copilot (VSCode)           |
| -------------- | ------------------------------------------ | --------------------------------- |
| **Rules**      | `.agent/rules/*.md`                        | `.github/copilot-instructions.md` |
| **Workflows**  | `.agent/workflows/*.md` → `/workflow-name` | Referenced as documentation       |
| **Skills**     | `.agent/skills/*/SKILL.md`                 | `.agent/skills/*.md` (legacy)     |
| **Activation** | Automatic (by description)                 | Context-aware                     |
| **Location**   | Mission Control view                       | Chat panel                        |

## 🎯 Configuration Files

### Google Antigravity IDE

```bash
.agent/
├── rules/
│   └── project-context.md          # Main project rules (Always On)
├── workflows/
│   ├── test-driven-development.md  # Invoke: /test-driven-development
│   ├── new-variable-type.md        # Invoke: /new-variable-type
│   └── README.md                   # Workflow catalog
└── skills/
    ├── parsing-workflow/
    │   └── SKILL.md                # Auto-activates for parsing tasks
    ├── new-plot-type/
    │   └── SKILL.md                # Auto-activates for viz tasks
    ├── shaper-pipeline/
    │   └── SKILL.md                # Auto-activates for data transforms
    ├── debug-async-parsing/
    │   └── SKILL.md                # Auto-activates for debugging
    └── README.md                   # Skills catalog
```

### GitHub Copilot (VSCode)

```bash
.github/
└── copilot-instructions.md         # All instructions in one file

.agent/
└── skills/
    ├── parsing-workflow.md         # Legacy format (compatible)
    ├── new-plot-type.md
    ├── shaper-pipeline.md
    └── debug-async-parsing.md
```

## 🚀 How to Use

### In Google Antigravity

1. **Rules**: Automatically applied
   - `project-context.md` is always active
   - Contains core guidelines, patterns, and constraints

2. **Workflows**: Invoke by name

   ```text
   /test-driven-development
   ```

   Agent guides you through each step sequentially

3. **Skills**: Automatically activated
   - Agent reads skill descriptions
   - If relevant to your task, applies the knowledge
   - No explicit invocation needed

### In GitHub Copilot (VSCode)

1. **Instructions**: Always active
   - `.github/copilot-instructions.md` loaded automatically
   - Contains all rules, patterns, and guidelines

2. **Skills**: Referenced as needed
   - Legacy `.md` files in `.agent/skills/`
   - Agent uses them contextually

3. **Workflows**: Documentation reference
   - Available for agent to follow
   - Not explicitly invoked but patterns are applied

## 🔄 Consistency Guarantees

Both IDEs follow the same:

### Core Principles

- ✅ **Test-Driven Development**: NO code without passing tests
- ✅ **Strong Typing**: mypy --strict on all code
- ✅ **Async-First Architecture**: Use submit*\*\_async + finalize*\* pattern
- ✅ **Layered Architecture**: Data (A) → Domain (B) → Presentation (C)
- ✅ **Zero Hallucination**: Never invent data or values
- ❌ **NO Git Operations**: STRICTLY forbidden for AI agents

### Architectural Patterns

- Factory Pattern for plots and shapers
- Facade Pattern for backend access
- Strategy Pattern for parsing
- Async workflows with concurrent.futures
- Immutable DataFrame transformations

### Code Quality

- Type hints on ALL functions and classes
- Unit tests before implementation
- Integration tests for workflows
- Black formatting
- Flake8 linting
- Mypy strict mode

### Autonomous Behavior

Both agents have FULL AUTONOMY to:

- Read/create/edit files
- Run tests and type checking
- Execute development commands
- Install dependencies
- Debug and analyze code

Both agents MUST NEVER:

- Execute git commands
- Commit or push changes
- Manipulate version control

## 📖 Documentation

### For Users

- [`.agent/README.md`](.agent/README.md) - General overview
- [`.agent/ANTIGRAVITY_README.md`](.agent/ANTIGRAVITY_README.md) - Antigravity-specific guide
- [`.agent/workflows/README.md`](.agent/workflows/README.md) - Workflow catalog
- [`.agent/skills/README.md`](.agent/skills/README.md) - Skills catalog

### For Developers

- [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) - Complete Copilot setup
- [`.agent/rules/project-context.md`](.agent/rules/project-context.md) - Core rules
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) - Contribution guidelines
- [`AI-SETUP.md`](../AI-SETUP.md) - AI setup guide

## 🔧 Maintenance

### When Changing Project Conventions

1. Update `.github/copilot-instructions.md` (VSCode)
2. Update `.agent/rules/project-context.md` (Antigravity)
3. Keep both in sync for consistency
4. Update relevant skills/workflows if needed

### Adding New Skills

1. Create `.agent/skills/skill-name/SKILL.md` (Antigravity format)
2. Create `.agent/skills/skill-name.md` (Legacy/Copilot format)
3. Add entry to `.agent/skills/README.md`
4. Ensure both versions have same content (different format)

### Adding New Workflows

1. Create `.agent/workflows/workflow-name.md`
2. Format:

   ```markdown
   # Workflow Title

   > **Invoke with**: `/workflow-name`
   > **Purpose**: Description

   ## Steps

   ...
   ```

3. Add entry to `.agent/workflows/README.md`
4. Test invocation in Antigravity

## ✅ Verification Checklist

To ensure dual-IDE compatibility:

- [ ] Core rules exist in both `.github/copilot-instructions.md` and `.agent/rules/project-context.md`
- [ ] Skills available in both formats: `*/SKILL.md` (Antigravity) and `*.md` (legacy)
- [ ] Workflows have proper invocation format (`/workflow-name`)
- [ ] README files up to date in each directory
- [ ] No IDE-specific code patterns (both must work)
- [ ] Autonomous operation rules consistent across both
- [ ] Git prohibition explicitly stated in both configurations

## 🎓 Learning Resources

### Google Antigravity

- [Official Documentation](https://antigravity.google/docs)
- [Rules & Workflows Guide](https://antigravity.google/docs/rules-workflows)
- [Skills Documentation](https://antigravity.google/docs/skills)
- [Agent Skills Standard](https://agentskills.io/)

### GitHub Copilot

- [Copilot Documentation](https://docs.github.com/copilot)
- [Workspace Instructions](https://code.visualstudio.com/docs/copilot/copilot-customization)

## 🤝 Contributing

When contributing AI configuration changes:

1. Test in BOTH IDEs if possible
2. Keep consistency between formats
3. Update all relevant README files
4. Follow existing naming conventions
5. Document why changes were made

---

**Result**: Seamless AI agent experience whether you're using Google Antigravity or GitHub Copilot in VSCode. Same rules, same patterns, same quality standards.
