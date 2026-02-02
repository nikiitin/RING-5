# Development Setup

Complete guide to setting up a RING-5 development environment.

## Prerequisites

- Python 3.12+
- Git
- Virtual environment tool (venv)
- Code editor (VS Code recommended)

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/USER/RING-5.git
cd RING-5
```

### 2. Create Virtual Environment

```bash
python3 -m venv python_venv
source python_venv/bin/activate  # Linux/macOS
# python_venv\Scripts\activate  # Windows
```

### 3. Install Development Dependencies

```bash
make dev
# Installs: pytest, mypy, black, flake8, and project dependencies
```

## Project Structure

```
RING-5/
├── src/                    # Source code
│   ├── parsers/           # Data layer (parsing)
│   ├── plotting/          # Presentation layer (plots)
│   └── web/               # Web interface
├── tests/                  # All tests
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── docs/                   # Documentation
├── portfolios/             # Saved portfolios
└── Makefile               # Build commands
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit code with your editor. Follow architecture guidelines in [Architecture.md](Architecture.md).

### 3. Run Tests

```bash
# All tests
make test

# Specific test file
pytest tests/unit/test_my_feature.py -v

# With coverage
pytest --cov=src tests/
```

### 4. Type Check

```bash
# Check all code
mypy src/ --strict

# Check specific file
mypy src/module/file.py --strict
```

### 5. Format Code

```bash
# Format all code
black src/ tests/

# Check formatting
black --check src/ tests/
```

### 6. Lint Code

```bash
flake8 src/ tests/
```

## Running the Application

### Development Mode

```bash
streamlit run app.py
```

### With Auto-Reload

Streamlit auto-reloads on file changes.

### Debug Mode

Add debug prints or use Python debugger:

```python
import pdb; pdb.set_trace()
```

## Common Development Tasks

### Adding a New Shaper

1. Create shaper class in `src/web/services/shapers/`
2. Register in `ShaperFactory`
3. Add UI component in `src/web/ui/components/shapers/`
4. Write tests in `tests/unit/test_shapers.py`

See [Adding-Shapers.md](Adding-Shapers.md).

### Adding a New Plot Type

1. Create plot class in `src/plotting/types/`
2. Inherit from `BasePlot`
3. Implement `create_figure()`
4. Register in `PlotFactory`
5. Write tests

See [Adding-Plot-Types.md](Adding-Plot-Types.md).

### Adding a New Page

1. Create page module in `src/web/pages/`
2. Define render function
3. Add to navigation in `app.py`
4. Write UI tests

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/

# With coverage report
pytest --cov=src --cov-report=html tests/
# Opens htmlcov/index.html
```

### Writing Tests

Follow TDD approach:
1. Write failing test
2. Implement feature
3. Test passes
4. Refactor

See [Testing-Guide.md](Testing-Guide.md).

## Code Quality

### Type Checking

All code must pass strict type checking:

```bash
mypy src/ --strict
```

**Requirements**:
- Type hints on all functions
- No implicit `Any`
- No untyped defs

### Code Formatting

Use Black for consistent formatting:

```bash
black src/ tests/
```

**Settings**: Default Black configuration (88 char line length).

### Linting

Flake8 checks for style issues:

```bash
flake8 src/ tests/
```

## Best Practices

1. **Follow Architecture**: Maintain layer separation
2. **Write Tests First**: TDD approach
3. **Type Everything**: Strict typing mandatory
4. **Document Why**: Explain non-obvious decisions
5. **Keep PRs Small**: Focused, reviewable changes
6. **Run All Checks**: Before committing

## Troubleshooting

### Import Errors

Ensure virtual environment is activated and dependencies installed.

### Test Failures

Check if changes broke existing tests. Fix tests or code as needed.

### Type Errors

Add missing type hints or fix type inconsistencies.

## Next Steps

- Testing: [Testing-Guide.md](Testing-Guide.md)
- Adding Features: [Adding-Plot-Types.md](Adding-Plot-Types.md), [Adding-Shapers.md](Adding-Shapers.md)
- Contributing: [../CONTRIBUTING.md](../CONTRIBUTING.md)
