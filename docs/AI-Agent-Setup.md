# AI Agent Setup

Guide to configuring AI assistants (GitHub Copilot, Cursor, etc.) for RING-5 development.

## Overview

RING-5 includes comprehensive instructions for AI coding assistants in `.github/copilot-instructions.md`. This guide explains how to leverage these instructions effectively.

## Supported AI Assistants

- **GitHub Copilot** (VS Code, Neovim, JetBrains)
- **Cursor** (AI-first editor)
- **Codeium** (VS Code, various editors)
- Other assistants supporting custom instructions

## Setup: GitHub Copilot

### VS Code

1. **Install Extension**:
   - Open Extensions (Ctrl+Shift+X)
   - Search "GitHub Copilot"
   - Install and authenticate

2. **Verify Instructions**:
   - Copilot automatically reads `.github/copilot-instructions.md`
   - No additional configuration needed

3. **Test**:
   ```python
   # Type: "Create a new shaper that filters by benchmark"
   # Copilot should suggest code following RING-5 patterns
   ```

### Neovim

1. **Install Plugin** (vim-plug):
   ```vim
   Plug 'github/copilot.vim'
   ```

2. **Configure**:
   ```vim
   :Copilot setup
   ```

3. **Copilot reads** `.github/copilot-instructions.md` automatically

## Setup: Cursor

1. **Open Project**:
   - File → Open Folder → Select RING-5

2. **Configure**:
   - Cursor auto-detects `.github/copilot-instructions.md`
   - Or manually add in Settings → AI → Custom Instructions

3. **Usage**:
   - Cmd/Ctrl+K for inline generation
   - Cmd/Ctrl+L for chat

## What the Instructions Provide

The `.github/copilot-instructions.md` file gives AI assistants:

### 1. Project Context
- RING-5 mission and domain (gem5 analysis)
- Architecture (layered, async, strict typing)
- Technology stack (Python 3.12+, Streamlit, Plotly, Pandas)

### 2. Design Principles
- Layered architecture (Data/Domain/Presentation)
- Async parsing patterns
- Design patterns (Strategy, Factory, Facade, Singleton)
- Testing protocol (TDD approach)

### 3. Coding Standards
- **Strong Typing**: Type hints mandatory on ALL code
- **Immutability**: DataFrames never modified in-place
- **Zero Hallucination**: Never guess data values
- **Test-Driven**: Tests before implementation

### 4. Critical Rules
- ⛔ **Git Prohibition**: AI NEVER executes git commands
- 📋 **Type Annotations**: Complete type hints required
- 🎯 **No Data Invention**: Real data only
- 🧪 **Testing Required**: No code without tests

### 5. Common Workflows
- Adding shapers
- Adding plot types
- Fixing bugs
- Async scanning/parsing patterns

### 6. Domain Knowledge
- gem5 stats.txt format
- Variable types (scalar, vector, distribution, histogram)
- Pattern aggregation system

## Using AI for Development

### Code Generation

**Request**: "Create a new filter shaper that filters rows by benchmark name"

**AI should**:
1. Create shaper class with proper types
2. Write unit tests first
3. Implement transformation logic
4. Register in factory
5. Follow immutability pattern

### Bug Fixing

**Request**: "Fix the bug in normalize shaper where division by zero occurs"

**AI should**:
1. Read existing code
2. Add test for edge case
3. Fix implementation
4. Verify all tests pass

### Refactoring

**Request**: "Refactor the plot factory to use type-based dispatch"

**AI should**:
1. Maintain existing API
2. Update all usages
3. Keep architectural layers separate
4. Run full test suite

## Best Practices

### 1. Be Specific

**Good**: "Create a shaper that normalizes values to range [0, 1] using min-max scaling"

**Bad**: "Add normalization"

### 2. Request Tests First

**Good**: "Write tests for a shaper that calculates geometric mean, then implement it"

**Bad**: "Implement geometric mean shaper"

### 3. Verify Outputs

Always:
- Run generated tests
- Type check with mypy
- Review code for architectural compliance

### 4. Iterate

If output doesn't match patterns:
- Point out specific issues
- Reference existing similar code
- Ask for corrections

## Example Interactions

### Adding a Feature

**You**: "I need a shaper that calculates speedup relative to a baseline. Follow TDD."

**AI Should**:
1. Write test:
   ```python
   def test_speedup_basic():
       data = pd.DataFrame({"ipc": [1.0, 2.0], "baseline": [1.0, 1.0]})
       config = {"metric": "ipc", "baseline": "baseline"}
       shaper = SpeedupShaper(config)
       result = shaper(data)
       assert result["speedup"].tolist() == [1.0, 2.0]
   ```

2. Implement shaper
3. Run tests
4. Register in factory

### Debugging

**You**: "The grouped bar plot isn't showing multiple groups correctly"

**AI Should**:
1. Read grouped bar implementation
2. Check data structure
3. Add debug test case
4. Fix grouping logic
5. Verify with test

### Refactoring

**You**: "The plot configuration code has lots of duplication. Refactor it."

**AI Should**:
1. Identify common patterns
2. Extract helper functions
3. Update all call sites
4. Ensure tests still pass
5. Type check all changes

## Troubleshooting

### AI Not Following Guidelines

**Issue**: AI suggests code that violates RING-5 patterns

**Solution**:
- Explicitly reference `.github/copilot-instructions.md`
- Quote specific rules: "Follow the async API pattern from instructions"
- Show example from existing code

### AI Suggests Git Commands

**Issue**: AI suggests git commit/push

**Solution**:
- Remind: "Never execute git commands per project rules"
- AI should only suggest code changes, not version control

### Missing Type Hints

**Issue**: Generated code lacks type annotations

**Solution**:
- Request: "Add complete type hints following mypy strict mode"
- Run: `mypy generated_file.py --strict`

## Advanced Usage

### Batch Operations

**Request**: "Create 5 test cases for the sort shaper covering edge cases"

**AI generates**:
- Empty DataFrame test
- Single row test
- Duplicate values test
- Null values test
- Large dataset test

### Architecture Questions

**Request**: "Should this shaper go in domain layer or presentation layer?"

**AI should**:
- Reference architectural guidelines
- Explain layer responsibilities
- Recommend correct location

### Code Review

**Request**: "Review this plot implementation for RING-5 compliance"

**AI checks**:
- Type hints completeness
- Architectural layer boundaries
- Test coverage
- Error handling
- Documentation

## Limitations

AI assistants:
- ❌ Cannot execute git commands
- ❌ Cannot deploy code
- ❌ May miss context from other files
- ✅ Can generate code following patterns
- ✅ Can write tests
- ✅ Can refactor existing code
- ✅ Can explain architecture

Always verify AI-generated code through testing and type checking.

## Next Steps

- Development: [Development-Setup.md](Development-Setup.md)
- Testing: [Testing-Guide.md](Testing-Guide.md)
- Contributing: [../CONTRIBUTING.md](../CONTRIBUTING.md)
