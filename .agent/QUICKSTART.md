# Agent Quickstart Guide

## 🚀 Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Start the Streamlit UI
streamlit run app.py
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src

# Run type checking
mypy src/
```

## 🛠 Common Workflows

### 1. Adding a New Metric
*   Update the relevant `ParserStrategy` in `src/parsers/` to capture the new key.
*   Add a test case in `tests/integration/` with a sample `stats.txt` snippet.

### 2. Creating a New Plot
*   Implement the visualizer in `src/plotting/visualizers/`.
*   Register the plot type in the `PlotFactory`.
*   Standard Font Sizes: Title (16pt), Axes (14pt), Legends (12pt).

### 3. Modifying Data Logic
*   Ensure all transformations return a **new** DataFrame (no `inplace=True`).
*   Verify that the logic is vectorized (uses NumPy/Pandas operations).

## 📋 Rule Checklist
- [ ] **Type Hints:** Are all function signatures typed?
- [ ] **No Git:** Did I avoid running any git commands?
- [ ] **Tests:** Did I write/update a test in `tests/`?
- [ ] **Docstrings:** Does the new code have Google-style docstrings?
