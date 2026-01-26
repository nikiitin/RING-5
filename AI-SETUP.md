# AI Assistant Configuration Guide

This directory contains configuration files that work across multiple AI coding assistants.

## 📁 File Structure

```
.
├── .agent/                          # Antigravity-specific rules
│   └── rules/
│       └── project-context.md      # Full detailed rules
├── .github/
│   └── copilot-instructions.md     # VS Code GitHub Copilot instructions
├── .vscode/
│   └── settings.json               # VS Code settings (Python, testing, AI)
├── .cursorrules                     # Cursor/Antigravity compact rules
├── .ai-assistant-guide.md          # Quick reference for all AI assistants
└── AI-SETUP.md                      # This file
```

## 🎯 Quick Start

### For VS Code Users (GitHub Copilot)

1. **GitHub Copilot reads**: `.github/copilot-instructions.md` automatically
2. **Quick reference**: Open `.ai-assistant-guide.md` when needed
3. **Settings**: `.vscode/settings.json` configures Python, testing, and AI features

**Pro Tips**:
- Ask Copilot: "What's the async parsing workflow?" → It knows the patterns
- Reference: "Follow the project rules" → It reads the instructions
- Context: Copilot sees `.agent/rules/project-context.md` in the workspace

### For Antigravity/Cursor Users

1. **Primary rules**: `.agent/rules/project-context.md` (full details)
2. **Compact rules**: `.cursorrules` (quick reference format)
3. **Quick reference**: `.ai-assistant-guide.md`

**Pro Tips**:
- Antigravity automatically loads `.agent/` directory
- `.cursorrules` provides inline context for Cursor IDE
- Both share the same architectural principles

## 🔧 Configuration Files Explained

### 1. `.github/copilot-instructions.md` (VS Code)
**Purpose**: GitHub Copilot's workspace instructions  
**Format**: Markdown with clear sections  
**Best for**: Detailed explanations, code examples, workflows

**What it contains**:
- Project identity and mission
- Architecture layers (A, B, C)
- Async API patterns
- Coding standards with examples
- Common workflows
- Testing protocols

**When Copilot uses it**:
- During code completions
- When you ask questions in chat
- For understanding project context

### 2. `.agent/rules/project-context.md` (Antigravity)
**Purpose**: Comprehensive rules for Antigravity  
**Format**: Structured markdown with frontmatter  
**Best for**: Complete architectural guidelines

**Triggers**: `always_on` (frontmatter)

### 3. `.cursorrules` (Cursor IDE)
**Purpose**: Compact rules for Cursor's AI  
**Format**: YAML-style key-value pairs  
**Best for**: Quick context loading

**Contains**: Condensed version of project rules

### 4. `.ai-assistant-guide.md` (Universal)
**Purpose**: Quick reference for ALL assistants  
**Format**: Cheatsheet-style markdown  
**Best for**: Quick lookups, common patterns

**Contains**:
- Quick start commands
- Architecture diagram
- DO/DON'T lists
- Key file locations
- Debugging tips

### 5. `.vscode/settings.json`
**Purpose**: VS Code workspace configuration  
**Format**: JSON  
**Best for**: Python environment, testing, formatting

**Configures**:
- Python interpreter path
- Testing framework (pytest)
- Code formatting (black, flake8)
- GitHub Copilot enablement
- File associations

## 🚀 Best Practices

### Using Both Antigravity and VS Code

1. **Maintain consistency**: All configs reference the same architectural principles
2. **Update together**: When rules change, update both `.github/copilot-instructions.md` and `.agent/rules/project-context.md`
3. **Use shared reference**: `.ai-assistant-guide.md` is the universal quick reference

### Asking AI Assistants

**Good prompts**:
- ✅ "Following the async API pattern, add scanning for distribution variables"
- ✅ "Create a new shaper using the Factory pattern from the rules"
- ✅ "Add tests following the testing protocol"

**Avoid**:
- ❌ "Make it work" (too vague)
- ❌ "Quick fix" (may violate architectural principles)
- ❌ Skipping tests

### Context Management

**When AI needs more context**:
1. Reference specific files: "Check `src/web/facade.py` for the pattern"
2. Point to examples: "See `tests/integration/test_gem5_parsing.py`"
3. Use the guide: "Follow the async workflow in `.ai-assistant-guide.md`"

## 🔄 Workflow Integration

### Development Cycle with AI

```
1. Start Task
   ├── Read .ai-assistant-guide.md (2 min)
   └── Ask AI: "What's the pattern for [task]?"

2. Implementation
   ├── AI generates code following rules
   ├── Review against .cursorrules checkpoints
   └── Verify layering (A/B/C)

3. Testing
   ├── Ask AI: "Generate tests for this function"
   ├── Run: make test
   └── Fix until 100% pass

4. Documentation
   ├── AI adds docstrings (Google style)
   └── Update guide if new pattern
```

### Git Workflow

**Committed files**:
- ✅ `.agent/` - Antigravity rules
- ✅ `.github/copilot-instructions.md` - VS Code instructions
- ✅ `.cursorrules` - Cursor rules
- ✅ `.ai-assistant-guide.md` - Universal guide
- ✅ `.vscode/settings.json` - VS Code config

**Ignored (in .gitignore)**:
- Personal AI settings
- API keys
- Local overrides

## 🛠️ Customization

### Adding New Patterns

When you establish a new pattern (e.g., new service layer):

1. Document it in `.agent/rules/project-context.md` (detailed)
2. Update `.github/copilot-instructions.md` (with examples)
3. Add to `.cursorrules` (compact reference)
4. Include in `.ai-assistant-guide.md` (quick reference)

### Project-Specific Commands

Add to `.ai-assistant-guide.md`:
```markdown
## Custom Commands

### Start Development Server
\`\`\`bash
source python_venv/bin/activate
streamlit run app.py
\`\`\`

### Run Specific Test Suite
\`\`\`bash
./python_venv/bin/pytest tests/unit/ -v
\`\`\`
```

## 📊 AI Configuration Matrix

| Feature | VS Code Copilot | Antigravity | Cursor |
|---------|----------------|-------------|---------|
| **Primary Config** | `.github/copilot-instructions.md` | `.agent/rules/` | `.cursorrules` |
| **Format** | Markdown | Markdown | YAML-style |
| **Auto-loaded** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Code completion** | ✅ Excellent | ✅ Excellent | ✅ Excellent |
| **Chat context** | ✅ Full workspace | ✅ Full workspace | ✅ Full workspace |
| **Custom instructions** | ✅ Per file | ✅ Per file | ✅ Global |
| **Shared guide** | `.ai-assistant-guide.md` | `.ai-assistant-guide.md` | `.ai-assistant-guide.md` |

## 🎓 Learning Resources

### Understanding the Rules

1. **Start here**: `.ai-assistant-guide.md` (5 min read)
2. **Deep dive**: `.agent/rules/project-context.md` (15 min read)
3. **See examples**: `tests/integration/` (practical usage)

### Testing Your Setup

Ask your AI assistant:
1. "What's the async parsing workflow?" → Should describe `submit_*_async()` pattern
2. "How do I add a new plot type?" → Should mention Factory pattern and specific files
3. "What are the three architecture layers?" → Should describe A (Data), B (Domain), C (Presentation)

If answers are correct, your setup is working! ✨

## 🆘 Troubleshooting

### AI Doesn't Follow Rules

1. **Check file location**: Is the config file in the right place?
2. **Reload window**: VS Code → Command Palette → "Developer: Reload Window"
3. **Verify content**: Open config file and ensure it's not corrupted
4. **Ask explicitly**: "Using the rules in .github/copilot-instructions.md, ..."

### Inconsistent Behavior Between AIs

- **Solution**: Update all config files together
- **Check**: Compare `.github/copilot-instructions.md` vs `.agent/rules/project-context.md`
- **Sync**: Use `.ai-assistant-guide.md` as the source of truth for common patterns

### AI Suggests Synchronous Wrappers

**AI might not see the async rule**. Respond:
> "No, follow the async API pattern from the project rules. Use `submit_parse_async()` + `finalize_parsing()`"

## 📝 Maintenance

**Weekly**:
- Review if new patterns emerged
- Update `.ai-assistant-guide.md` with new common tasks

**After major changes**:
- Update all config files
- Test with both AI assistants
- Verify tests still pass: `make test`

**Monthly**:
- Review AI suggestions quality
- Refine rules if AI consistently misunderstands
- Update examples

## 🌟 Pro Tips

1. **Be specific**: Reference file names and patterns from the guides
2. **Iterate**: If AI misses the mark, point to the specific rule
3. **Context window**: Keep `.ai-assistant-guide.md` open for quick AI reference
4. **Test immediately**: Run `make test` after AI generates code
5. **Feedback loop**: If AI consistently violates a rule, make it more explicit

---

**Need help?** Ask your AI assistant:
- "Show me the AI configuration structure"
- "What rules should you follow for this project?"
- "Explain the async workflow pattern"

Your AI assistant should now answer using the configured knowledge! 🚀
