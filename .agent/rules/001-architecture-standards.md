---
description: Architecture standards, layering, and design patterns.
globs: src/**/*.py
---

# 001-architecture-standards.md

## 1. The System Architect

You design systems with strict separation of concerns, clear boundaries, and extensibility in mind.

## 2. The Three Layers (Strict Separation)

You must enforce a strict separation of concerns. The code must be divided into three distinct layers. **Never mix these.**

### Layer A: The Data Layer (Ingestion)

- **Responsibility:** Reading raw files (`stats.txt`, `config.ini`).
- **Pattern:** **Strategy Pattern**. Create an interface `ParserStrategy` with a method `parse()`. Implement concrete classes like `Gem5TxtParser` or `Gem5JsonParser`.
- **Output:** Returns strictly typed Data Classes or Pydantic models, NEVER raw dictionaries.

### Layer B: The Domain Layer (Business Logic)

- **Responsibility:** Statistical analysis, aggregating metrics (e.g., calculating IPC from `committedInsts / numCycles`), and filtering.
- **Pattern:** **Chain of Responsibility** or **Pipe & Filter**. Data should flow through transformation steps that produce a final, immutable DataFrame.
- **Rule:** This layer should know NOTHING about Streamlit or Plotly. It operates purely on data.

### Layer C: The Presentation Layer (UI & Viz)

- **Responsibility:** Displaying data.
- **Pattern:** **Factory Pattern**. Use a `PlotFactory` class to generate Plotly figures.
  - _Example:_ `PlotFactory.create_line_chart(df, x="cycles", y="ipc")`.
  - _Why:_ This ensures every single plot in the app shares the same "High-End Conference" styling (fonts, colors, background) defined in one place.
- **Framework:** Streamlit code lives here. It calls Layer B to get data, then Layer C (Factory) to get the plot.

## 3. Mandatory Design Patterns

Apply these patterns whenever the context matches:

| Pattern                        | Context                        | Implementation                                                                                                   |
| :----------------------------- | :----------------------------- | :--------------------------------------------------------------------------------------------------------------- |
| **Strategy**                   | Parsing different file formats | `class Gem5Parser(ABC): ...`                                                                                     |
| **Factory Method**             | Creating visualizations        | `class FigureFactory` with methods like `build_heatmap()`                                                        |
| **Singleton**                  | Configuration Management       | `ConfigManager` ensures only one instance of app settings exists.                                                |
| **Facade**                     | API Simplification             | Create a `SimulationAnalysisFacade` that the Streamlit UI calls, hiding the complexity of parsing and filtering. |
| **DTO (Data Transfer Object)** | Moving data between layers     | Use Python `dataclasses` (frozen) to pass data. Do not pass `dict`.                                              |

## 4. Repository Pattern

- **Port:** The `AbstractRepository` interface (or Protocol) defining the contract.
- **Adapter:** Concrete implementations (e.g., `CsvSimulationRepository`, `SqlAlchemyRepository`).
- **Minimum API:** A repository should ideally only expose `add(entity)` and `get(id)`.
- **One Aggregate = One Repository:** Repositories must strictly return Aggregate Roots.

## 5. Unit of Work (UoW)

- **Responsibility:** Manages the context of an atomic operation/transaction.
- **Implementation:** Use a **Python Context Manager** (`with uow:`).
- **Explicit Commits:** Prefer requiring an explicit `uow.commit()` call.
- **Rollback by Default:** Must rollback if an exception occurs or if `commit()` wasn't called.

## 6. Dependency Injection

- **Explicit Dependencies:** Pass dependencies (UoW, Adapters) as arguments to handlers/services.
- **Composition Root (`bootstrap.py`):** Maintain a central script responsible for wiring the application together.
- **No Hidden Imports:** Avoid patterns that require monkeypatching (`mock.patch`).

## 7. Functional Core, Imperative Shell (FCIS)

- **Functional Core (Domain):** Pure functions/objects that take simple data structures and return them. Infinitely testable without mocks.
- **Imperative Shell (Adapters/Services):** Gathers I/O, feeds it to the core, and applies changes.
- **Hoist I/O:** Move disk access and network calls to the extreme edges of the application (Adapters).

## 8. Backend-Frontend Sync

- Any change to the backend data processing logic **MUST** immediately trigger updates in the Streamlit session state.
- Use `st.cache_data` for expensive parsing operations to keep the UI snappy.
- Ensure cache invalidation happens when source files change.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 001**
