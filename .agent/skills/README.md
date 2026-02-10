# RING-5 Skills

Skills are reusable packages of knowledge that extend what the agent can do. They're automatically activated when relevant to your task.

## Available Skills

### `parsing-workflow`
**Activates when**: Working with gem5 stats parsing, scanning variables, or data loading  
**Contains**: Complete async-first parsing workflow patterns  
**Format**: [SKILL.md](parsing-workflow/SKILL.md)

Key knowledge:
- 4-phase workflow: Scan → Select → Parse → Load
- Async API patterns with concurrent.futures
- Error handling and validation
- Streamlit integration
- Performance optimization

---

### `new-plot-type`
**Activates when**: Adding new visualizations or custom chart types  
**Contains**: Step-by-step plot implementation guide  
**Format**: [SKILL.md](new-plot-type/SKILL.md)

Key knowledge:
- Factory pattern implementation
- BasePlot interface
- Plotly figure creation
- Streamlit UI integration
- Unit testing patterns

---

### `shaper-pipeline`
**Activates when**: Implementing data transformations or processing pipelines  
**Contains**: Shaper creation and pipeline patterns  
**Format**: [SKILL.md](shaper-pipeline/SKILL.md)

Key knowledge:
- Shaper interface and protocol
- Pipeline composition
- Built-in shapers catalog
- Custom shaper creation
- Testing strategies

---

### `debug-async-parsing`
**Activates when**: Troubleshooting parsing failures or async issues  
**Contains**: Debugging guide for async parsing workflows  
**Format**: [SKILL.md](debug-async-parsing/SKILL.md)

Key knowledge:
- Common failure modes
- Timeout diagnostics
- Concurrent.futures debugging
- Log analysis patterns
- Resolution strategies

---

## Skill Structure

Each skill follows the [Agent Skills standard](https://agentskills.io/) with:

```
skills/
└── skill-name/
    ├── SKILL.md          # Main instructions (required)
    ├── examples/         # Reference implementations (optional)
    ├── scripts/          # Helper scripts (optional)
    └── resources/        # Templates and assets (optional)
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Clear description for agent to decide when to use this skill
---

# Skill Title

Main content with detailed instructions, patterns, and examples.

## When to use this skill

Specific scenarios where this skill is relevant.

## How to use it

Step-by-step guidance and conventions.
```

## How Skills Work

### Progressive Disclosure

1. **Discovery**: Agent sees list of available skills with names/descriptions
2. **Activation**: If relevant, agent reads full SKILL.md content
3. **Execution**: Agent follows skill's instructions while working

### Automatic Activation

You don't need to explicitly invoke skills. The agent decides based on:
- Your task description
- Current context
- Skill descriptions

However, you can mention a skill by name to ensure it's used.

## Creating New Skills

1. Create folder: `.agent/skills/my-skill/`
2. Add `SKILL.md` with YAML frontmatter
3. Write clear description (this is how agent chooses the skill)
4. Include practical examples and patterns
5. Add references to relevant code
6. Update this README

### Best Practices

✅ **DO**:
- Keep skills focused on one domain
- Write specific, keyword-rich descriptions
- Include decision trees for complex scenarios
- Reference actual code paths
- Provide complete code examples

❌ **DON'T**:
- Create "do everything" mega-skills
- Use vague descriptions
- Forget to update when code changes
- Include outdated patterns

## Skill vs Workflow

**Use a Skill when**: You want reusable knowledge the agent automatically applies

**Use a Workflow when**: You want a specific sequence of steps to execute

**Example**:
- Skill: "How to implement shapers" (knowledge)
- Workflow: "Create a new percentage shaper" (specific task)

## Legacy Format

Files in `.agent/skills/*.md` (not in subdirectories) are legacy format compatible with GitHub Copilot. For dual IDE support, skills are available in both formats:

- `skills/skill-name/SKILL.md` - Google Antigravity format (YAML frontmatter)
- `skills/skill-name.md` - Legacy format (maintained for compatibility)

## See Also

- [Workflows](../workflows/) - Step-by-step processes
- [Rules](../rules/) - Project guidelines and constraints
- [Agent Skills Standard](https://agentskills.io/) - Open standard specification
- [GitHub Copilot Instructions](../../.github/copilot-instructions.md) - VSCode configuration
