# RING-5 Project Documentation

## 1. Project Overview

**RING-5** is a statistical analysis engine designed to evaluate Gem5 simulation outputs, specifically targeting Transactional Semantics in Serverless/FaaS environments. It provides a structured pipeline to parse, transform, and visualize hierarchical simulation data.

## 2. Core Tech Stack

- **Language:** Python 3.12+ (Strictly Typed)
- **Parsing:** Regex-based async parsers with Perl integration for legacy support.
- **Data Engine:** Pandas (Immutable transformations) & NumPy.
- **Frontend:** Streamlit.
- **Visualization:** Plotly (Graph Objects).
- **Quality Assurance:** Pytest (Unit/Integration), MyPy (Strict Type Checking), Hypothesis (Property-based testing).

## 3. Architectural Design

The project follows a **Layered Architecture** with a strict separation of concerns to ensure maintainability and testability.

### Layer A: Data Ingestion (Adapters)

- **Responsibility:** Reading `stats.txt` and `config.ini` files.
- **Pattern:** Strategy Pattern for supporting different Gem5 versions/formats.
- **Location:** `src/parsers/`

### Layer B: Domain Logic (Core)

- **Responsibility:** Statistical calculations, data normalization, and metric aggregation.
- **Pattern:** Pipe & Filter for data transformations; Repository Pattern for data access.
- **Location:** `src/core/`

### Layer C: Presentation (Web & Viz)

- **Responsibility:** Rendering the Streamlit UI and generating Plotly figures.
- **Pattern:** Factory Pattern for plot generation to ensure consistent styling.
- **Location:** `src/web/`, `src/plotting/`

## 4. Key Workflows

### Parsing Workflow

1.  **Scan:** Identify `stats.txt` and corresponding `config.ini`.
2.  **Select:** Determine the correct `ParserStrategy`.
3.  **Parse:** Extract hierarchical metrics using optimized regex.
4.  **Load:** Convert to a Tidy (Long-format) Pandas DataFrame.

### Testing Workflow (TDD)

1.  **Red:** Write a test in `tests/` for the new functionality.
2.  **Green:** Implement the minimal logic in the appropriate layer.
3.  **Refactor:** Clean code while maintaining type safety and vectorization rules.
4.  **Verify:** Run `pytest` and `mypy --strict`.

## 5. Coding Standards

- **Strong Typing:** All functions must have complete type annotations.
- **Vectorization:** No explicit `for` loops over Pandas DataFrames.
- **Error Handling:** Fail fast with specific custom exceptions (e.g., `MetricNotFoundError`).
- **Documentation:** Google-style docstrings for all public classes and functions.

## 6. Directory Structure

```
RING-5/
├── src/
│   ├── core/           # Domain logic and data processing
│   ├── parsers/        # Gem5 file ingestion strategies
│   ├── plotting/       # Plotly visualizers and factories
│   └── web/            # Streamlit frontend
├── tests/              # Unit, integration, and e2e tests
├── .agent/             # Agent-specific rules and workflows
└── app.py              # Application entrypoint
```
