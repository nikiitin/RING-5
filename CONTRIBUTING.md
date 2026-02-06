# Contributing to RING-5

Thank you for your interest in contributing to RING-5! This document provides guidelines and information for contributors.

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/vnicolas/RING-5.git
cd RING-5
python -m venv python_venv
source python_venv/bin/activate  # On Windows: python_venv\Scripts\activate
pip install -e .
```

### 2. Install Development Tools

```bash
pip install pytest pytest-cov pytest-timeout black flake8 mypy pre-commit
```

### 3. Setup Pre-commit Hooks

Pre-commit hooks automatically check code quality before each commit:

```bash
pre-commit install
```

This will run:

- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
- **isort**: Import sorting
- **bandit**: Security checks

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/ -v                    # Unit tests only
pytest tests/integration/ -v             # Integration tests only
pytest tests/ui_logic/ -v                # UI logic tests only

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Type Checking

RING-5 uses **mypy strict mode** with zero tolerance for type errors:

```bash
# Check entire codebase
mypy src/ --strict

# Check specific file
mypy src/web/services/variable_service.py --strict
```

**Current Status**: 0 errors in 117 source files ✅

### Code Formatting

```bash
# Format code with black
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### Linting

```bash
# Run flake8
flake8 src/ tests/ --max-line-length=100

# Check for dead code
vulture src/ tests/ --min-confidence 80
```

## Continuous Integration

### GitHub Actions CI Pipeline

Every push and pull request triggers automated checks:

**Jobs**:

1. **test**: Runs full test suite with coverage
2. **type-safety**: Enforces mypy strict compliance
3. **code-quality**: Checks formatting and linting

**Requirements for Merge**:

- ✅ All tests passing (653/653)
- ✅ Type safety (0 mypy errors)
- ✅ Code formatted with black
- ✅ No critical flake8 violations

### Local CI Simulation

Run all CI checks locally before pushing:

```bash
# 1. Format code
black src/ tests/

# 2. Run linters
flake8 src/ tests/ --max-line-length=100

# 3. Type check (strict)
mypy src/ --strict

# 4. Run tests
make test

# 5. Check coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Code Quality Standards

### Type Annotations (MANDATORY)

Every function, method, and class must have complete type hints:

```python
# ✅ GOOD
def process_data(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Process dataframe with threshold."""
    result: pd.DataFrame = df[df["value"] > threshold]
    return result

# ❌ BAD
def process_data(df, threshold):  # No type hints
    return df[df["value"] > threshold]
```

### Documentation (REQUIRED)

All public functions and classes need docstrings:

```python
def calculate_speedup(baseline: float, experiment: float) -> float:
    """
    Calculate speedup relative to baseline.

    Args:
        baseline: Baseline execution time
        experiment: Experiment execution time

    Returns:
        Speedup value (baseline / experiment)

    Raises:
        ValueError: If experiment is zero
    """
    if experiment == 0:
        raise ValueError("Experiment time cannot be zero")
    return baseline / experiment
```

### Testing (COMPREHENSIVE)

- **Unit tests**: Test individual functions/methods
- **Integration tests**: Test component interactions
- **UI tests**: Test Streamlit components (mocked)

**Coverage Target**: Maintain 77%+ coverage

```python
# Example unit test structure
class TestCalculateSpeedup:
    """Tests for calculate_speedup function."""

    def test_basic_speedup(self) -> None:
        """Should calculate correct speedup."""
        assert calculate_speedup(100, 50) == 2.0

    def test_raises_on_zero_experiment(self) -> None:
        """Should raise ValueError for zero experiment time."""
        with pytest.raises(ValueError):
            calculate_speedup(100, 0)
```

## Architecture Guidelines

### Layered Architecture

RING-5 follows strict architectural layers:

```
UI Layer (Streamlit)
    ↓ uses
Service Layer (Business Logic)
    ↓ uses
Data Layer (Parsing, CSV)
```

**Rules**:

- ❌ UI components NEVER contain business logic
- ❌ Services NEVER import Streamlit
- ✅ All business logic goes in services
- ✅ Services are pure Python, fully testable

### Service Pattern Example

```python
# ❌ BAD - Business logic in UI
def render_component():
    data = st.session_state["data"]
    if len(data) > 0:
        result = data.groupby("category").mean()  # Business logic!
        st.dataframe(result)

# ✅ GOOD - Service handles logic
class DataService:
    @staticmethod
    def aggregate_by_category(data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data by category with mean."""
        return data.groupby("category").mean()

def render_component():
    data = st.session_state["data"]
    if len(data) > 0:
        result = DataService.aggregate_by_category(data)
        st.dataframe(result)
```

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow code quality standards
- Add/update tests
- Update documentation

### 3. Run Pre-commit Checks

```bash
pre-commit run --all-files
```

### 4. Commit

```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit Message Format**:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

### 6. PR Requirements

Your PR will be automatically checked by CI. Required:

- ✅ All tests pass
- ✅ No type errors
- ✅ Code formatted with black
- ✅ Coverage maintained (≥77%)

## Common Tasks

### Adding a New Service

1. Create service file: `src/web/services/my_service.py`
2. Add comprehensive type hints
3. Write unit tests: `tests/unit/test_my_service.py`
4. Ensure 0 mypy errors: `mypy src/web/services/my_service.py --strict`

### Adding a New Plot Type

1. Create plot class: `src/plotting/types/my_plot.py`
2. Register in `PlotFactory`
3. Add integration test: `tests/integration/test_my_plot.py`
4. Update documentation

### Refactoring a Component

1. Write tests for current behavior (if missing)
2. Make changes incrementally
3. Run tests after each change
4. Verify: `make test && mypy src/ --strict`

## Questions?

- Check existing code for examples
- Read `.agent/` documentation for detailed guides
- Open an issue for clarification

## Code of Conduct

- Be respectful and professional
- Focus on the code, not the person
- Welcome newcomers
- Give constructive feedback

---

Thank you for contributing to RING-5! 🚀
