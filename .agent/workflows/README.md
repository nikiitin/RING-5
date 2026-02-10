# RING-5 Workflows

Workflows are step-by-step processes for common development tasks. In Google Antigravity, invoke them with `/workflow-name`.

## Available Workflows

### `/release-branch-review` ⭐ NEW

**Purpose**: Comprehensive, publication-grade review before merging to main/develop
**When to use**: Before any merge to protected branches (main, develop)
**Complexity**: Advanced
**Estimated Time**: 30-60 minutes

The ultimate pre-merge review workflow - leaves no stone unturned.

**10 Review Phases:**

1. **Scope Assessment** - Quantify and classify the change
2. **Commit History Audit** - Verify commit hygiene and logical sequencing
3. **Architectural Integrity** - Check layer boundaries and patterns
4. **Type Safety Audit** - Ensure complete type coverage
5. **Test Coverage Analysis** - Verify tests exist and pass
6. **Security Scan** - Static analysis and vulnerability check
7. **Performance Review** - Algorithmic and Pandas anti-patterns
8. **Documentation Review** - API docs and changelogs
9. **Code Quality Deep Dive** - Code smells and naming conventions
10. **Integration & Regression** - Full test suite and smoke tests

**Critical**: No merge without sign-off on all blocking criteria.

---

### `/test-driven-development`

**Purpose**: Guide all code changes through the TDD process
**When to use**: Every time you write new code, fix bugs, or refactor
**Complexity**: Fundamental

Enforces the golden rule: Write Test → See it Fail → Write Code → See it Pass → Refactor

Key steps:

1. Write the test first (unit or integration)
2. Run test to see it fail
3. Implement minimum code to pass
4. Verify test passes
5. Run all related tests
6. Type check (mypy --strict)
7. Format code (black)

**Critical**: NO code is committed until tests pass.

---

### `/new-variable-type`

**Purpose**: Add support for new gem5 statistics variable types
**When to use**: Extending parser for new gem5 stat formats
**Complexity**: Advanced

Guides through complete implementation:

1. Analyze gem5 stat format
2. Create Perl parser script
3. Register in TypeMapper
4. Update scanner logic
5. Create unit tests
6. Create integration tests
7. Test with real gem5 data

Covers: Parser implementation, testing, type mapping, and validation.

---

## Using Workflows

### In Google Antigravity

Simply type `/workflow-name` in the Agent input:

```
/test-driven-development
```

The agent will guide you through each step sequentially.

### In GitHub Copilot (VSCode)

Workflows are available as reference documentation. The agent will follow the patterns described when appropriate.

### Chaining Workflows

Workflows can call other workflows. For example, `/new-variable-type` internally follows `/test-driven-development` principles.

## Creating New Workflows

1. Create `workflow-name.md` in `.agent/workflows/`
2. Use this template:

```markdown
# Workflow Title

> **Invoke with**: `/workflow-name`
> **Purpose**: Clear description
> **Complexity**: Simple/Intermediate/Advanced

## Overview

Brief explanation of what the workflow achieves.

## Steps

### Step 1: [Action]

Detailed instructions...

### Step 2: [Action]

Detailed instructions...

...
```

3. Add entry to this README
4. Test by invoking in Antigravity

## Best Practices

- **Keep workflows focused**: One clear goal per workflow
- **Make steps actionable**: Each step should be executable
- **Include examples**: Show concrete code/commands
- **Define success criteria**: How to verify each step worked
- **Reference other workflows**: Build on existing patterns
- **Test thoroughly**: Ensure workflow is repeatable

## See Also

### 📜 Rule System (The Brain)

All workflows must adhere to the rules defined in `.cursor/rules/`:

- **Identity (`000`)**: Zero Hallucination Policy.
- **Architecture (`001`)**: Layers (A/B/C) and Separation of Concerns.
- **Data Science (`002`)**: Vectorization Standards.
- **Engineering (`003`)**: Strong Typing.
- **QA (`004`)**: Fixtures as Architecture.

### 📚 Skills

- [Skills](../skills/) - Reusable knowledge packages
- [GitHub Copilot Instructions](../../.github/copilot-instructions.md) - VSCode AI configuration
