# RING-5 AI Capabilities - Quick Reference

## 🚀 Autonomous Powers (No Permission Needed)

The AI has **FULL AUTONOMY** to execute these actions:

### ✅ File Operations

- Read any file in the workspace
- Create new files (code, tests, configs, documentation)
- Edit existing files
- Search codebase (grep, semantic search, file search)

### ✅ Testing & Quality

- Run all tests (`make test`, `pytest`)
- Run specific test files or functions
- Check test coverage
- Type check with mypy
- Lint with flake8
- Format with black

### ✅ Development

- Install dependencies
- Run Streamlit app
- Execute Python scripts
- Debug code
- Analyze logs and data
- Generate demo outputs

### ✅ Code Quality

- Automatic formatting
- Automatic linting
- Strict type checking
- Performance testing
- Coverage reports

## ❌ Absolute Prohibitions

### Git Commands - NEVER ALLOWED

The AI must **NEVER** execute any git commands:

- `git add`, `git commit`, `git push`, `git pull`
- `git checkout`, `git branch`, `git merge`, `git rebase`
- `git stash`, `git reset`, `git revert`, `git tag`
- ANY command starting with `git`

**Why**: Version control is a human responsibility. The AI must never manipulate repository history.

## 📋 Core Operating Principles

### 1. Test-Driven Development

- Write tests FIRST
- Run test (should fail)
- Implement feature
- Run test (should pass)
- Run all tests (no regression)

### 2. Strong Typing

- ALL functions must have type hints
- Use mypy strict mode
- No implicit `Any`
- TypedDict for structured data

### 3. Zero Hallucination

- Never invent data
- Never guess values
- If data doesn't exist, say so
- Fail fast on errors

### 4. Architectural Layers

```
Layer C (Presentation) → Streamlit UI
         ↓
Layer B (Domain)      → Business logic (no UI imports)
         ↓
Layer A (Data)        → File I/O, parsing
```

### 5. Async Patterns

```python
# Always follow this pattern:
futures = service.submit_async(...)
results = [f.result() for f in futures]
data = service.finalize(results)
```

### 6. Immutability

```python
# ✅ CORRECT
result = data.drop(columns=['x'])

# ❌ WRONG
data.drop(columns=['x'], inplace=True)
```

### 7. Publication Quality

- Vector-ready plots
- 14pt+ fonts
- Clear legends
- Reproducible outputs

## 🧠 Problem-Solving Approach

1. **Understand**: Read request, identify core issue
2. **Research**: Search codebase, read existing code
3. **Plan**: Break into tasks, plan tests first
4. **Implement**: Write tests, then code
5. **Validate**: Run tests, type check, format
6. **Report**: Summarize what was done

## 🔄 Common Workflows

### Adding a Feature

1. Search for similar features
2. Write tests (should fail)
3. Implement feature
4. Tests pass
5. Type check + format

### Fixing a Bug

1. Create test that reproduces bug
2. Locate bug in code
3. Fix and verify test passes
4. Run all tests (no regression)

### Adding a Plot

1. Write unit tests
2. Implement plot class
3. Register in factory
4. Write integration tests
5. Validate with real data

### Async Operations

1. Submit async work
2. Wait for futures
3. Finalize/aggregate results
4. Store in session state

## 🎯 Domain Knowledge

### gem5 Statistics

- **Scalar**: Single values
- **Vector**: Arrays with entries
- **Distribution**: Min/max ranges
- **Histogram**: Binned data
- **Configuration**: Metadata

### Pattern Aggregation

```
system.cpu0.numCycles  ┐
system.cpu1.numCycles  ├→ system.cpu\d+.numCycles [vector]
system.cpu2.numCycles  ┘   entries: ["0", "1", "2"]
```

**Impact**: Reduces 12,000+ variables to ~700 (94% reduction)

## 📊 Quick Commands

### Testing

```bash
make test                    # Run all tests
pytest tests/unit/file.py -v # Run specific file
pytest --cov=src tests/      # With coverage
```

### Code Quality

```bash
black src/ tests/            # Format code
flake8 src/ tests/           # Lint code
mypy src/ --strict           # Type check
```

### Development

```bash
streamlit run app.py         # Start app
./python_venv/bin/pytest     # Run tests
```

## 🎓 Decision Framework

### Act Autonomously (DO IT)

- Creating files
- Running tests
- Type checking
- Formatting code
- Reading files
- Searching codebase
- Debugging
- Installing dependencies

### Ask First

- User intent is ambiguous
- Multiple valid approaches
- Breaking API changes
- Architecture decisions

### Default Behavior

When in doubt: Implement the most reasonable solution based on existing patterns, test it, then report what was done and why.

## 📚 Key Files

- `.github/copilot-instructions.md` - Full AI brain (870 lines)
- `src/parsing/gem5/impl/scanning/pattern_aggregator.py` - Pattern detection
- `src/web/facade.py` - Backend entry point
- `tests/` - Test suite (500+ tests)

## ✨ Autonomy Level

**MAXIMUM** - Execute freely, report results, never touch git.

The AI can do everything a senior developer does EXCEPT version control.
