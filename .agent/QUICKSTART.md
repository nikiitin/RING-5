# Quick Start: Using AI Agents in RING-5

Choose your IDE and follow the corresponding guide.

## 🚀 Google Antigravity IDE

### First Time Setup
1. Open RING-5 in Antigravity IDE
2. Rules are automatically loaded from `.agent/rules/`
3. Skills appear in Customizations panel
4. You're ready to go!

### Using Workflows
Invoke workflows by typing slash commands in Agent input:

```
/test-driven-development
```

Available workflows:
- `/test-driven-development` - TDD process for all code changes
- `/new-variable-type` - Add support for new gem5 variable types

### Using Skills
Skills activate automatically when relevant. No action needed!

Just describe your task:
```
"I need to parse gem5 stats from this directory"
→ parsing-workflow skill auto-activates
```

Available skills:
- `parsing-workflow` - gem5 statistics parsing
- `new-plot-type` - Adding visualizations
- `shaper-pipeline` - Data transformations
- `debug-async-parsing` - Debugging async issues

### Using Rules
Rules are always active. The agent follows them automatically:
- TDD mandatory
- Strong typing (mypy --strict)
- Async-first patterns
- Zero hallucination
- NO git operations

---

## 💻 GitHub Copilot (VSCode)

### First Time Setup
1. Open RING-5 in VSCode
2. GitHub Copilot loads `.github/copilot-instructions.md` automatically
3. Chat with Copilot using Cmd/Ctrl + I
4. You're ready to go!

### Using Skills
Skills are available as reference documentation:
- Located in `.agent/skills/*.md`
- Copilot references them contextually
- No explicit invocation needed

Example:
```
You: "How do I add a new plot type?"
Copilot: [References .agent/skills/new-plot-type.md]
```

### Using Workflows
Workflows are patterns Copilot follows automatically:
- Test-Driven Development enforced
- Architecture patterns applied
- Code quality standards maintained

### Using Rules
All rules from `.github/copilot-instructions.md` are always active:
- Same rules as Antigravity
- Same patterns enforced
- Same quality standards

---

## 🎯 Common Tasks

### Task: Parse gem5 Statistics

**Antigravity**:
```
User: I need to parse gem5 stats from /data/stats
Agent: [Activates parsing-workflow skill]
      I'll guide you through the 4-phase workflow:
      1. Scanning for variables...
```

**Copilot**:
```
User: Parse gem5 stats from /data/stats
Copilot: I'll implement the async parsing workflow:
         [Follows patterns from parsing-workflow.md]
```

### Task: Add New Plot Type

**Antigravity**:
```
User: I want to create a radar chart visualization
Agent: [Activates new-plot-type skill]
      Following the Factory pattern approach...
```

**Copilot**:
```
User: Create a radar chart visualization
Copilot: I'll implement a new plot type:
         [Follows patterns from new-plot-type.md]
```

### Task: Write New Feature with TDD

**Antigravity**:
```
/test-driven-development
Agent: Step 1: Write the test first...
```

**Copilot**:
```
User: Add percentage shaper
Copilot: Following TDD:
         1. First, let's write the test...
```

---

## 📊 Comparison

| Feature | Antigravity | Copilot |
|---------|------------|---------|
| Rules | Auto-applied | Auto-applied |
| Workflows | `/workflow-name` | Patterns followed |
| Skills | Auto-activate | Contextual reference |
| Invocation | Explicit commands | Natural language |
| Monitoring | Task Groups view | Chat history |
| Multi-agent | Mission Control | Single agent |

---

## 💡 Pro Tips

### Both IDEs
- ✅ Be specific in your requests
- ✅ Reference file paths when relevant
- ✅ Ask for tests first (TDD)
- ✅ Request type checking after changes
- ❌ Don't ask for git operations (forbidden)

### Antigravity Specific
- Use `/workflow-name` for step-by-step guidance
- Mention skill names to ensure activation
- Check Task Groups for progress tracking
- Use feedback artifacts to guide refinements

### Copilot Specific
- Use "How do I..." to get skill guidance
- Ask "Following TDD..." to invoke workflow patterns
- Request "Check the existing pattern..." for consistency
- Use inline suggestions for quick edits

---

## 🆘 Troubleshooting

### Skills Not Activating (Antigravity)
1. Check skill descriptions are clear
2. Mention skill name explicitly
3. Verify SKILL.md has YAML frontmatter

### Rules Not Being Followed (Either IDE)
1. Verify `.agent/rules/project-context.md` exists (Antigravity)
2. Verify `.github/copilot-instructions.md` exists (Copilot)
3. Restart IDE to reload configurations

### Workflows Not Working (Antigravity)
1. Ensure `/` prefix in command
2. Check workflow file exists in `.agent/workflows/`
3. Verify proper markdown format

---

## 📚 Learn More

- **Dual IDE Guide**: [.agent/DUAL_IDE_SETUP.md](.agent/DUAL_IDE_SETUP.md)
- **Antigravity Guide**: [.agent/ANTIGRAVITY_README.md](.agent/ANTIGRAVITY_README.md)
- **Workflows Catalog**: [.agent/workflows/README.md](.agent/workflows/README.md)
- **Skills Catalog**: [.agent/skills/README.md](.agent/skills/README.md)
- **Implementation Summary**: [.agent/IMPLEMENTATION_SUMMARY.md](.agent/IMPLEMENTATION_SUMMARY.md)

---

**Result**: Consistent AI behavior across both IDEs with same rules, patterns, and quality standards! 🎉
