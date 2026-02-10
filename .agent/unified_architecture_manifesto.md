# The Unified Architecture Manifesto: Blueprint for the Ideal Application

**Version:** 2.0.0 (The "Leviathan" Edition)
**Author:** Antigravity (Lead Software Architect & Scientific Data Engineer)
**Date:** October 2023
**Status:** DEFINITIVE BLUEPRINT
**Target Audience:** Senior Engineers, Architects, and Researchers

---

## Table of Contents

1.  Preamble: The Pursuit of Scientific Rigor
2.  Part I: The Core Philosophy - Structural Integrity
    - The Domain-Driven Design Imperative
    - The Repository Pattern
    - The Unit of Work
    - The Message Bus
3.  Part II: The Data Engine - High-Performance Analysis
    - The Laws of Vectorization
    - Memory Layout and Strides
    - The "Tidy Data" Principle
    - Split-Apply-Combine
4.  Part III: The Quality Shield - Verification and Validation
    - The Testing Pyramid
    - Fixtures as Architecture
    - Mocking Strategies
5.  Part IV: The Ideal Application Blueprint
    - Directory Structure
    - The Golden Path
    - Configuration Strategy
6.  Part V: The Code Review Protocol - Guardian of Quality
    - The Review Philosophy
    - The Ten Phases of Release Review
    - Blocking Criteria
    - The Review Mindset
    - Review Anti-Patterns

---

## Preamble: The Pursuit of Scientific Rigor in Software

## The Crisis of Complexity

We stand at a precipice. In the domain of high-performance simulation and data analysis, specifically within the Gem5 research ecosystem, the complexity of our tools often outstrips our ability to reason about them. Note the following observation:

> "The software architecture of a system is the set of structures needed to reason about the system." — _Architecture Patterns with Python_

If we cannot reason about our software, we cannot reason about our science. If our cache coherence protocol simulation is built upon a "Big Ball of Mud" architecture, can we truly trust the latency numbers it spits out?

We are not building "scripts". Scripts are ephemeral; they live for a day. We are building **Scientific Instruments**. Like a particle accelerator or an electron microscope, our software must be:

1.  **Calibration-Ready:** Verifyable against known ground truths.
2.  **Modular:** Components can be swapped without collapsing the whole.
3.  **Observability:** Internal states must be transparent.

## The Four Pillars

This manifesto synthesizes the deepest insights from four foundational pillars of modern Python engineering:

1.  **Structural Integrity:** _Architecture Patterns with Python_ (Percival & Gregory). This provides the "Skeleton" (DDD, Clean Architecture).
2.  **Data Proficiency:** _Python for Data Analysis_ (McKinney). This provides the "Muscle" (NumPy, Pandas, Vectorization).
3.  **Verification Discipline:** _Test-Driven Development with Python_ (Percival). This provides the "Immune System" (Red-Green-Refactor).
4.  **Testing Strategy:** _Python Testing with pytest_ (Okken). This provides the "Nervous System" (Fixtures, Parametrization).

Our goal is nothing less than the **Ideal Correctly Architected Application**. This document is not a suggestion. It is a blueprint.

---

## Part I: The Core Philosophy - Structural Integrity

### 1.1 The Domain-Driven Design (DDD) Imperative

The core of our application is the **Domain Model**. The Domain Model represents the platonic ideal of the problem we are solving. It contains the business rules, the logic, and the scientific invariants.

### The Dependency Rule

The most critical rule in this manifesto is the **Dependency Rule**:

> **Source code dependencies must point only inward, toward higher-level policies.**

- **Wrong:** The Domain imports SQLAlchemy. (The model depends on the database).
- **Wrong:** The Domain imports Streamlit. (The model depends on the UI).
- **Right:** The Infrastructure (SQLAlchemy) imports the Domain.
- **Right:** The Presentation (Streamlit) imports the Domain.

### The Building Blocks of the Domain

We reject the use of "anemic" classes (data holders with no logic) and "god classes" (logic holders with no data). We embrace rich models.

#### 1. Entities: The Identity Holders

An **Entity** is an object defined by its identity, not its attributes. If you change the "Name" of a `Simulation`, it is still the same simulation.

```python
# src/domain/model.py

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Simulation:
    """
    An Entity representing a single run of the Gem5 Simulator.
    Identity is defined by the 'run_id'.
    """
    run_id: str  # Identity
    timestamp: datetime
    config: dict
    status: str = "PENDING"
    _stats: List['StatMetric'] = field(default_factory=list)

    def complete(self):
        """Business Logic: State transition."""
        if not self._stats:
            raise ValueError("Cannot complete a simulation with no stats.")
        self.status = "COMPLETED"

    def add_metric(self, metric: 'StatMetric'):
        """Business Logic: Invariant protection."""
        if self.status == "COMPLETED":
            raise RuntimeError("Cannot add metrics to a completed simulation.")
        self._stats.append(metric)

    def __hash__(self):
        return hash(self.run_id)

    def __eq__(self, other):
        if not isinstance(other, Simulation):
            return False
        return self.run_id == other.run_id
```

**Why this matters:**

- Identity logic is encapsulated.
- State transitions (`complete()`) are protected. You cannot accidentally set `status = "COMPLETED"` without checking invariants.
- It is pure Python. No database code here.

#### 2. Value Objects: The Immutable Truths

A **Value Object** is defined by its attributes. It has no identity. If you change an attribute, it is a different object.

- _Rule:_ Prefer Value Objects over primitives. Never pass raw `int` for cycles; pass `Ticks(1000)`.

```python
# src/domain/values.py

from dataclasses import dataclass

@dataclass(frozen=True)
class Ticks:
    """
    Value Object for simulation time.
    Immutable (frozen=True).
    Prevents 'Integer Obsession' antipattern.
    """
    value: int

    def __add__(self, other: 'Ticks') -> 'Ticks':
        if not isinstance(other, Ticks):
            raise TypeError("Can only add Ticks to Ticks")
        return Ticks(self.value + other.value)

    def to_seconds(self, frequency_hz: float) -> float:
        return self.value / frequency_hz
```

**Why this matters:**

- Type Safety: `def analyze(start: Ticks, end: Ticks)` is safer than `def analyze(start: int, end: int)`.
- Logic reuse: The `to_seconds` conversion lives in one place, not scattered across 50 scripts.

#### 3. Aggregates: The Transaction Boundary

An **Aggregate** is a cluster of objects treated as a unit for the purpose of data changes. The **Aggregate Root** is the only object that outside objects are allowed to hold references to.

- _Example:_ `Simulation` is an Aggregate Root. `StatMetric` is internal to it.
- _Rule:_ You cannot delete a `StatMetric` directly. You must ask the `Simulation` to remove it. This ensures the `Simulation` can update its internal caches or re-validate its state.

### 1.2 The Repository Pattern: Abstracting Storage

The Repository pattern is the boundary between the Domain and the persistent storage (Database, Filesystem, S3).
It creates the illusion that all objects are in memory.

### The Problem with Active Record (Django Style)

In Django/ActiveRecord:

```python
user = User.objects.get(id=1)
user.save()
```

This couples your domain objects to the database. If you want to switch from SQL to a CSV file (common in research), you have to rewrite your entire domain.

### The Repository Solution

1.  **The Abstract Interface (in Domain):**

    ```python
    # src/domain/ports.py
    class AbstractRepository(ABC):
        @abstractmethod
        def add(self, simulation: Simulation):
            raise NotImplementedError

        @abstractmethod
        def get(self, run_id: str) -> Simulation:
            raise NotImplementedError
    ```

2.  **The Concrete Implementation (in Adapters):**

    ```python
    # src/adapters/repository.py
    class SqlAlchemyRepository(AbstractRepository):
        def __init__(self, session):
            self.session = session

        def add(self, simulation: Simulation):
            self.session.add(simulation)

        def get(self, run_id: str) -> Simulation:
            return self.session.query(Simulation).filter_by(run_id=run_id).one()
    ```

3.  **The Fake Implementation (for Tests):**

    ```python
    class FakeRepository(AbstractRepository):
        def __init__(self):
            self._simulations = set()

        def add(self, simulation: Simulation):
            self._simulations.add(simulation)

        def get(self, run_id: str) -> Simulation:
            return next(s for s in self._simulations if s.run_id == run_id)
    ```

**Why this matters:**

- **Testing Speed:** We can run 1000 unit tests using `FakeRepository` in 0.1 seconds. Using a real DB would take 10 seconds.
- **Decoupling:** We can delay the choice of database until late in the project.

### 1.3 The Unit of Work (UoW): Atomic Operations

How do we ensure data integrity? What if we save the `Simulation` but crash before saving the `Stats`?
The **Unit of Work** pattern manages the "Atomic Transaction".

### The API

```python
# src/service_layer/unit_of_work.py

class AbstractUnitOfWork(ABC):
    simulations: AbstractRepository

    def __enter__(self) -> 'AbstractUnitOfWork':
        return self

    def __exit__(self, *args):
        self.rollback()  # Default action

    @abstractmethod
    def commit(self):
        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        raise NotImplementedError
```

### The Usage

```python
def ingest_simulation(run_id: str, file_path: str, uow: AbstractUnitOfWork):
    with uow:
        # 1. Load data
        simulation = parse_gem5_stats(file_path, run_id)

        # 2. Add to repo
        uow.simulations.add(simulation)

        # 3. Commit (Magic happens here)
        uow.commit()
```

If `parse_gem5_stats` fails, `uow.commit()` is never called. `__exit__` calls `uow.rollback()`. The database remains clean. We never have "half-imported" data.

### 1.4 The Message Bus: Decoupling via Events

As the system grows, we get requirements like:

- "When a simulation is imported, check for cache anomalies."
- "When a simulation is imported, send a Slack notification."
- "When a simulation is imported, update the Dashboard cache."

If we put all this in `ingest_simulation`, it becomes a Monster Function.
Solution: **Domain Events**.

### The Event

```python
# src/domain/events.py
@dataclass
class SimulationImported(Event):
    run_id: str
```

### The Handler

```python
# src/service_layer/handlers.py
def check_cache_anomalies(event: SimulationImported, uow: AbstractUnitOfWork):
    with uow:
        sim = uow.simulations.get(event.run_id)
        if sim.l2_miss_rate > 0.5:
            # Raise alert...
```

### The Bus (The Nervous System)

```python
# src/service_layer/messagebus.py
def handle(event: Event, uow: AbstractUnitOfWork):
    queue = [event]
    while queue:
        evt = queue.pop(0)
        for handler in HANDLERS[type(evt)]:
            try:
                # Handlers can spawn new events!
                new_events = handler(evt, uow)
                queue.extend(new_events)
            except Exception:
                # Error handling strategy
                continue
```

This transforms our application from a procedural script into a **Reactive System**.

---

## Part II: The Data Engine - High-Performance Analysis

> "Data analysis is 80% cleaning and preparation." — _Python for Data Analysis_

While Part I defines the _structure_, Part II defines the _muscle_. For Gem5 analysis, we deal with gigabytes of trace data. Standard Python objects (`list`, `dict`) are memory hogs and slow. `for` loops are the enemy. We must think in **Vectors**.

### 2.1 The Laws of Vectorization

### Rule #1: No For-Loops over Data

Python interpretation overhead is massive.

- _Bad:_
  ```python
  # 10ms for 1M items
  result = []
  for x in large_list:
      result.append(x * 2)
  ```
- _Good:_
  ```python
  # 0.1ms for 1M items
  result = large_array * 2
  ```
  This is **Broadcasting**. The loop happens in C, inside the CPU's SIMD registers.

### Rule #2: Filter with Boolean Masks

Do not iterate to filter.

- _Bad:_ `[x for x in data if x > 0]`
- _Good:_ `data[data > 0]`

### Rule #3: The "UFunc" (Universal Function)

NumPy functions (`np.exp`, `np.log`, `np.sqrt`) are typically 10-100x faster than `math.exp` looped over a list.

### 2.2 Memory Layout and Strides

Understanding `ndarray` internals is the key to Zero-Copy operations.
An array is:

1.  **Buffer:** A raw block of bytes.
2.  **Dtype:** How to interpret bytes (e.g., `float64`).
3.  **Shape:** Dimensions (e.g., `(100, 100)`).
4.  **Strides:** How many bytes to jump to get to the next element.

### Zero-Copy Reshaping

```python
arr = np.zeros((100, 100))
flat = arr.ravel()  # Might copy
transpose = arr.T   # NEVER copies. It just swaps the strides.
```

### Implications for Gem5 Traces

Gem5 traces are often time-series.
`Time x Metric` vs `Metric x Time`.

- We prefer **Time** as the contiguous dimension (Row-Major) because we usually analyze one metric over time (e.g., "Show me IPC over the last 1M cycles").
- This maximizes CPU cache hits (spatial locality).

### Memory Mapping (`np.memmap`)

For 100GB traces, we cannot load everything into RAM.

```python
def load_massive_trace(path):
    return np.memmap(path, dtype='float32', mode='r', shape=(1000000, 100))
```

The OS manages paging. We treat the file as an array. This is critical for scaling to "Full-System" Gem5 simulations.

### 2.3 The "Tidy Data" Principle

We adhere to Hadley Wickham’s definition of Tidy Data:

1.  **Each variable** forms a column.
2.  **Each observation** forms a row.
3.  **Each type of observational unit** forms a table.

### The "Long Format" Preference

In intermediate steps, we prefer Long Format:

```text
Tick | Core | Metric | Value
0    | 0    | IPC    | 1.2
0    | 0    | Misses | 5
100  | 0    | IPC    | 1.1
```

Vs Wide Format:

```text
Tick | Core0_IPC | Core0_Misses | Core1_IPC ...
```

**Why?**

- Adding a new metric (or Core) in Wide Format requires a schema change (new column).
- Adding a new metric in Long Format is just a new row. It is **Schema-Agnostic**.
- Long Format works natively with `groupby()` and `seaborn`.

### 2.4 The Split-Apply-Combine Paradigm

This is our primary mechanism for aggregation.

### 1. Split

Divide the dataset into groups.

- `df.groupby('Benchmark')`
- `df.groupby(pd.cut(df['IPC'], bins=10))` (Binning)

### 2. Apply

Apply a function to each group independently.

- **Aggregation:** Reduce group to a single value (`mean`, `sum`).
  - `df.groupby('Core').mean()`
- **Transformation:** Same shape as original group.
  - `df.groupby('Core').transform(lambda x: x - x.mean())` (Demeaning)
- **Filtration:** Discard groups.
  - `df.groupby('Core').filter(lambda x: x['IPC'].mean() > 1.0)`

### 3. Combine

Pandas handles this automatically.

### Advanced Pattern: The Custom Aggregator

```python
def percentile_99(x):
    return x.quantile(0.99)

grouped.agg({
    'IPC': ['mean', 'std', percentile_99],
    'L2Misses': 'sum'
})
```

This single pass produces a hierarchical column index with all stats.

---

## Part III: The Quality Shield - Verification and Validation

> "Code without tests is broken by design." — _Test-Driven Development with Python_

We do not write "scripts that seem to work". We write verified systems.
Scientific software without tests is indistinguishable from a random number generator.

### 3.1 The Testing Pyramid

1.  **Unit Tests (70%):**
    - **Scope:** Single function or class.
    - **Deps:** Mocked/Faked (Use `FakeRepository`).
    - **Speed:** < 1ms per test.
    - **Location:** `tests/unit/`
    - _Purpose:_ Verify logic and edge cases.

2.  **Integration Tests (20%):**
    - **Scope:** Interaction between layers (Service -> Repo -> DB).
    - **Deps:** Real (SQLite, Real Files).
    - **Speed:** ~100ms per test.
    - **Location:** `tests/integration/`
    - _Purpose:_ Verify wiring and schema compatibility.

3.  **End-to-End (E2E) Tests (10%):**
    - **Scope:** Full application (Streamlit UI).
    - **Deps:** Full System.
    - **Speed:** Seconds per test.
    - **Location:** `tests/e2e/`
    - _Purpose:_ Verify "Happy Path" user flows.

### 3.2 Fixtures as Architecture

In `unittest`, we used `setUp()` and `tearDown()`. This leads to "General Setup" bloat where `setUp` creates objects that only 10% of tests user.
In `pytest`, we use **Fixtures**.

### Dependency Injection via Fixtures

Fixtures are our DI framework for tests.

```python
# tests/conftest.py

@pytest.fixture
def repo():
    return FakeRepository()

@pytest.fixture
def bus(repo):
    # The Bus depends on the Repo. Pytest handles the resolution.
    return MessageBus(repo=repo)

@pytest.fixture
def service(bus):
    return SimulationService(bus=bus)
```

### Hierarchy of `conftest.py`

We leverage scoped conftests.

- `tests/conftest.py`: Global fixtures (e.g., `temp_db`).
- `tests/unit/conftest.py`: Unit-specific fixtures (e.g., `fake_repo`).
- `tests/integration/conftest.py`: Integration-specific fixtures (e.g., `postgres_db`).

This ensures Unit tests _cannot_ accidentally use the real Database fixture. The namespace protects us.

### 3.3 Mocking Strategies: London vs. Chicago

### The London School (Mockist)

- **Philosophy:** Isolate the Unit Under Test (UUT). Mock _everything_ it touches.
- **Pros:** Exact pinpointing of bugs. Fast.
- **Cons:** Brittle. if you rename a method in the dependency, the mock doesn't break, the test passes, but production fails.

### The Chicago School (Classicist)

- **Philosophy:** Use real objects (or high-fidelity Fakes) for dependencies. Only mock IO.
- **Pros:** Resilience. Refactoring internals doesn't break tests.
- **Cons:** Slower. "Distance" from bug can be higher.

### Our Strategy: The Hybrid

1.  **For Domain Entities (Values, Aggregates):** **Chicago School.**
    - Never mock a `Simulation` object. Just instantiate a real one. They are fast memory objects.
    - Never mock a Value Object.
2.  **For Boundaries (Repositories, APIs):** **London School / Fakes.**
    - Mock the `FileSystem`. Mock the `Database`.
    - Use `FakeRepository` (In-Memory Set) instead of `Mock()` where possible. Fakes have contract fidelity; Mocks do not.

### Anti-Pattern: Patching internals

- _Bad:_ `@patch('src.service.Simulation.calculate_ipc')`
- _Why:_ You are mocking a private implementation detail. If you move `calculate_ipc` to a helper function, test breaks.
- _Rule:_ Only mock **Interfaces** (Abstract Base Classes), not concrete implementations.

---

## Part IV: The Ideal Application Blueprint

This section synthesizes the philosophies into a concrete architectural layout for the "Perfect Application". This is the directory structure we aspire to.

### 4.1 Directory Structure

The structure represents the architecture. A developer should scream "Architecture!" just by looking at the folders.

```text
ring5/
├── src/
│   ├── ring5/                  # The Package
│   │   ├── domain/             # PURE PYTHON. The "Inner Hexagon".
│   │   │   ├── events.py       # Domain Events (DTOs)
│   │   │   ├── model.py        # Entities, Value Objects, Aggregates
│   │   │   ├── commands.py     # Command DTOs
│   │   │   └── exceptions.py   # Domain-specific errors (not HTTP 404s)
│   │   │
│   │   ├── adapters/           # INFRASTRUCTURE. "The Adapters".
│   │   │   ├── repository.py   # SqlAlchemy/FileSystem implementations
│   │   │   ├── orm.py          # Database Mappings
│   │   │   ├── loaders.py      # Gem5 stats.txt parsers
│   │   │   └── notifications.py# Email/Slack adapters
│   │   │
│   │   ├── service_layer/      # ORCHESTRATION. "The Application".
│   │   │   ├── services.py     # Entry points for use cases
│   │   │   ├── unit_of_work.py # UoW implementation
│   │   │   ├── messagebus.py   # Event dispatcher
│   │   │   └── handlers.py     # Logic that subscribes to events
│   │   │
│   │   ├── entrypoints/        # THE OUTSIDE WORLD. "The Ports".
│   │   │   ├── cli.py          # Command Line Interface (Click/Typer)
│   │   │   ├── api.py          # FastAPI app (if needed)
│   │   │   └── streamlit_app.py# Streamlit Dashboard
│   │   │
│   │   ├── visualization/      # PRESENTATION (Data-specific).
│   │   │   ├── factory.py      # PlotFactory (Constructs Figures)
│   │   │   ├── theme.py        # Color palettes, font configs
│   │   │   └── layouts.py      # Complex grid layouts
│   │   │
│   │   └── config.py           # Configuration Strategy (Pydantic Settings)
│   │
│   └── setup.py
│
├── tests/
│   ├── conftest.py             # Global fixtures
│   ├── unit/                   # Tests for Domain/Services (Fast) (Chicago School)
│   │   ├── test_model.py
│   │   └── test_services.py
│   ├── integration/            # Tests for Adapters (Medium) (Db interactions)
│   │   └── test_repository.py
│   └── e2e/                    # Tests for Entrypoints (Slow) (Selenium/StreamlitRunner)
│       └── test_cli.py
│
├── data/                       # Sample data / Gold Reference data
├── docs/                       # Architecture decisions records (ADRs)
├── Makefile                    # Automation (test, lint, format)
├── requirements.txt
└── pyproject.toml              # Tool configuration (Black, Isort, Mypy)
```

### 4.2 The Golden Path (The Life of a Request)

How does data verify the architecture? Let's trace a "Load Stats" command.

1.  **Entrypoint:** User clicks "Upload" in `streamlit_app.py`.
    - The buffer is received.
    - The Entrypoint creates a `LoadSimulationCommand` (DTO).
2.  **Service Call:** UI calls `messagebus.handle(command)`.
    - _Crucially: UI does not parse the file. UI does not speak to DB._
3.  **Handler:** The bus routes `LoadSimulationCommand` to `handlers.load_simulation`.
    - handler initiates `uow`.
4.  **Adapter:** The handler delegates to `adapters.loaders.Gem5Parser` to parse the buffer into a `Simulation` Aggregate.
    - The Parser is purely functional.
5.  **Repository:** The handler calls `uow.simulations.add(simulation)`.
    - The simulation is added to the session's identity map.
6.  **Commit:** The handler calls `uow.commit()`.
    - Database transaction logic executes (BEGIN, INSERT, MIT... COMMIT).
7.  **Event:** `uow.commit()` triggers the Message Bus.
    - Event `SimulationAdded` is collected from `simulation.events`.
    - The Bus publishes `SimulationAdded`.
8.  **Reaction:** New Handler `precompute_cache_stats` runs.
    - It wakes up, calculates, and saves derived stats using a new UoW interaction.
9.  **Return:** Service returns success (or ID) to UI. UI displays a success message.

### 4.3 Configuration Strategy

We avoid global state. We avoid `os.environ.get()` scattering.
We use **Pydantic Settings**.

```python
# src/ring5/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    DB_URL: str = "sqlite:///ring5.db"
    DEBUG_MODE: bool = False
    THEME_PRIMARY_COLOR: str = "#FF5733"

    class Config:
        env_file = ".env"

# Singleton instance
settings = Settings()
```

**Injection:**
Services that need config should accept it in `__init__`.

```python
class PlotFactory:
    def __init__(self, theme_color: str = settings.THEME_PRIMARY_COLOR):
        self.color = theme_color
```

This allows us to inject "Test Configs" (e.g., different colors, test DB URLs) seamlessly during testing.

### 4.4 The "Four Rules" of the Ideal Application

1.  **The Rule of Boundaries:** Dependencies never cross boundaries without an Interface (ABC). The Domain is sacred.
2.  **The Rule of IO:** Core logic is pure. All IO (Disk, Network, DB) is pushed to the edge (Adapters). IO is the most common cause of test slowness and flakiness.
3.  **The Rule of Data:** Data is immutable once it enters the Domain logic. If you need to change it, create a new derived dataset.
4.  **The Rule of Science:** Every metric calculation must be unit-tested against a "Hand-Calculated" oracle. (e.g., A CSV with 3 rows where we know the exact mean). We never trust the library blindly. Hallucination in science is fraud.

### 4.5 Managing Complexity with "Bounded Contexts"

As the application grows, the `domain` folder will bloat.
We apply **Bounded Contexts** to split the domain vertically.

- **Context 1: Ingestion.** Focus: Parsing, Validating, Storage.
- **Context 2: Analysis.** Focus: Pandas, Aggregation, Statistics.
- **Context 3: Reporting.** Focus: Plotting, LaTeX generation.

Each context can theoretically have its own Architecture. The Ingestion context might be detailed DDD. The Analysis context might be a functional pipeline.
The Service Layer acts as the translator between these contexts.

---

## Part V: The Code Review Protocol - Guardian of Quality

> "A release is not a commit, it's a contract." — The Antigravity Council

Code review is not a bureaucratic hurdle. It is the **final quality gate** before code becomes part of the permanent historical record. In scientific software, this is especially critical: a bug that passes review may corrupt months of simulation data.

### 5.1 The Review Philosophy

We distinguish between two review intensities:

**Standard Review** (Feature branches → develop):

- Quick turnaround (1-2 hours)
- Focus on correctness and tests
- Single reviewer sufficient

**Release Review** (develop → main, major features):

- Thorough multi-phase analysis
- Focus on architecture, security, and long-term maintainability
- Multiple reviewers or extended single review

### 5.2 The Ten Phases of Release Review

For merges to protected branches, we execute a systematic 10-phase review:

| Phase                          | Focus               | Goal                     |
| ------------------------------ | ------------------- | ------------------------ |
| **1. Scope Assessment**        | Quantify changes    | Understand risk level    |
| **2. Commit History**          | Hygiene check       | Clean, logical history   |
| **3. Architectural Integrity** | Layer boundaries    | No dependency violations |
| **4. Type Safety**             | mypy --strict       | No type holes            |
| **5. Test Coverage**           | Tests exist & pass  | No untested paths        |
| **6. Security Scan**           | Bandit, pip-audit   | No vulnerabilities       |
| **7. Performance**             | Complexity analysis | No O(n²) surprises       |
| **8. Documentation**           | API docs current    | No undocumented APIs     |
| **9. Code Quality**            | Smells detection    | No technical debt        |
| **10. Integration**            | Full test suite     | No regressions           |

See `.agent/workflows/release-branch-review.md` for the complete protocol.

### 5.3 Blocking Criteria (Non-Negotiable)

A merge is **BLOCKED** if any of these fail:

1. **Tests**: Any test failure blocks the merge. Period.
2. **Type Safety**: `mypy --strict` must pass with zero errors.
3. **Security**: Critical or High severity vulnerabilities block.
4. **Architecture**: Layer boundary violations block.
5. **Regressions**: Any functionality that previously worked must continue to work.

### 5.4 The Review Mindset

**As a Reviewer, Ask:**

- "If I inherit this code in 6 months, will I understand it?"
- "Does this code fail gracefully or silently corrupt data?"
- "Are the tests actually testing behavior, or just lines of code?"
- "Could this change break something I haven't considered?"
- "Is this the simplest solution that could work?"

**As an Author, Provide:**

- Clear PR description explaining the "why"
- Link to related issues or documentation
- Note any areas you're uncertain about
- Self-review before requesting others

### 5.5 Review Anti-Patterns

**The Rubber Stamp:**

> "LGTM" after 30 seconds on a 500-line PR.

**The Gate Keeper:**

> Blocking PRs for stylistic preferences not in the style guide.

**The Archaeologist:**

> Demanding rewrites of unrelated legacy code in every PR.

**The Silent Disapprover:**

> Leaving comments without marking approval or requesting changes.

**The Correctness:**

- Review thoroughly or decline to review
- Apply guidelines consistently
- Stay focused on the PR's scope
- Be explicit about approval status

---

## Epilogue: The Discipline of Maintenance

Architecture is not a "one-time" setup. It is a continuous gardening process.
Entropy acts heavily on codebases. The natural state is disorder.
We resist entropy through:

1.  **Strict Code Reviews** referencing this manifesto. "This PR violates Rule 1.1 (Dependency Rule)."
2.  **Continual Refactoring** as we learn more about the domain. Ideally, the `Refactor` step of TDD is never skipped.
3.  **Zero Broken Windows:** Fix small issues (lint warnings, slight coupling) immediately before they fester.

This manifesto is the contract between the development team and the scientific integrity of the project.

**Signed,**
_The Antigravity Architectural Council_

---

## Appendix A: The Python Performance Handbook

> "Premature optimization is the root of all evil." — Donald Knuth

However, _late_ optimization is impossible if the architecture is wrong.

## A.1 The Complexity Cheat Sheet

Before optimization, check your algorithms.

| Structure | Operation | Complexity | Note                            |
| :-------- | :-------- | :--------- | :------------------------------ |
| **List**  | Append    | O(1)       | Amortized                       |
| **List**  | Insert(0) | O(N)       | **Avoid!** Shifts all elements. |
| **List**  | Access(i) | O(1)       | Fast                            |
| **Set**   | Add       | O(1)       | Hashing                         |
| **Set**   | Contains  | O(1)       | **Use this for lookups!**       |
| **Dict**  | Get/Set   | O(1)       | Hashing                         |
| **Deque** | PopLeft   | O(1)       | Use for Queues                  |

## A.2 Pandas Optimization Checklist

1.  [ ] **Load Less Data:** Use `usecols` in `read_csv`.
    - _Why:_ Loading unused columns wastes RAM/CPU.
2.  [ ] **Downcast Types:** Use `float32` instead of `float64` if precision allows. Use `category` for strings with low cardinality.
    - _Code:_ `df['Status'] = df['Status'].astype('category')`
    - _Impact:_ 10x memory reduction for string columns.
3.  [ ] **Vectorize Strings:** Use `df['str_col'].str.contains()`? **No.**
    - _Faster:_ Convert to category first, or use list comprehensions for complex regex if vectorization is slow.
4.  [ ] **Avoid `apply(axis=1)`:** It is a loop in Python.
    - _Alternative:_ `df['A'] + df['B']` (Vectorized).
    - _Alternative:_ `np.vectorize(func)(df['A'], df['B'])`.

## A.3 The Profiling Strategy

Don't guess. Measure.

1.  **Macro (Whole Program):** `python -m cProfile -o profile.stats src/entrypoints/cli.py`
    - Visualize with `snakeviz`.
2.  **Micro (Function):** `line_profiler`.
    - Decorate with `@profile`. Run with `kernprof -l -v script.py`.
3.  **Nano (Snippet):** `%timeit` in IPython/Jupyter.

---

## Appendix B: The Anti-Pattern Bestiary

Recognize these monsters to defeat them.

## B.1 The God Object ("SimulationManager")

- **Symptoms:** A class named `Manager`, `System`, or `Processor` that has 50 methods and 3000 lines of code. It imports everything.
- **Why it's bad:** High coupling. Impossible to test partial functionality.
- **The Fix:** Split into specialized Services. `SimulationIngester`, `SimulationAnalyzer`, `SimulationReporter`.

## B.2 The Anemic Domain Model

- **Symptoms:** `Simulation` class has only data fields (`run_id`, `stats`). All logic is in `SimulationService`.
- **Why it's bad:** Violation of OOP. Data and behavior are separated. Logic is duplicated across services.
- **The Fix:** Move logic _into_ the Entity. "Tell, Don't Ask". Instead of `service.calculate_speedup(sim)`, use `sim.calculate_speedup()`.

## B.3 The "Shotgun Surgery"

- **Symptoms:** To add a new metric (e.g., "L3 Miss Rate"), you have to edit:
  1.  The Parser
  2.  The Database Schema
  3.  The Model
  4.  The HTML Template
  5.  The Export Logic
- **Why it's bad:** Fragile. Missing one spot causes bugs.
- **The Fix:** Use Metadata-Driven architectures or Generic "Metric" dictionaries where appropriate (Part II: Tidy Data).

## B.4 The Mockery (Over-Mocking)

- **Symptoms:** Tests look like `mock_cursor.execute.return_value.fetchall.return_value = [...]`.
- **Why it's bad:** You are testing the implementation of the database driver, not your logic.
- **The Fix:** Use a **FakeRepository** (In-Memory implementation of the AbstractRepository).

---

## Appendix C: Security & Reproducibility in Science

## C.1 The Crisis of Reproducibility

If you run the Simulation twice, you must get the _exact same bits_.

### The Seed Strategy

Gem5 (and Python's `random`) are deterministic _if seeded_.

- **Rule:** The `Simulation` aggregate must store the `RandomSeed`.
- **Rule:** We never rely on System Time for logic, only for logging.

### The Bitwise Verify

We verify raw output against a "Gold Standard" hash.

```python
def verify_integrity(file_path, expected_hash):
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    assert sha.hexdigest() == expected_hash
```

## C.2 Input Sanitization (Yes, even for Researchers)

Researchers often assume "Safe Inputs". This is wrong.
A malicious `config.ini` could contain:
`[General] OutputDir = /etc/passwd`

- **Rule:** All file paths from user input must be validated against a whitelist of allowed directories.
- **Rule:** Never use `eval()` to parse configs. Use `ast.literal_eval()` or `json.loads`.

---

## Appendix D: The Refactoring Guide

## D.1 The Refactoring Loop

Refactoring is not "cleaning up". It is a disciplined transformation that preserves behavior.

1.  **Check:** Ensure all tests pass.
2.  **Transform:** Apply a specific move (e.g., "Extract Method").
3.  **Verify:** Run tests.
4.  **Commit:** `git commit -m "Refactor: Extract Method"`

## D.2 Common Moves

### Extract Method

- **Context:** A function is too long (screen height).
- **Action:** Select a block of code. Move it to a new function. Name it after _what_ it does, not _how_ it does it.

### Replace Conditional with Polymorphism

- **Context:**
  ```python
  if type == 'O3': calculate_o3()
  elif type == 'Minor': calculate_minor()
  ```
- **Action:** Create a class hierarchy (`AbstractCPU`). Move logic into `calculate()` method of subclasses.

### Introduce Parameter Object

- **Context:** `def plot(x, y, color, title, xlabel, ylabel, font_size)`
- **Action:** Create a dataclass `PlotConfig`. `def plot(data, config: PlotConfig)`.

## D.3 Legacy Code Strategy

"Legacy Code is code without tests." — Michael Feathers.

**How to refactor Legacy Code:**

1.  **Identify Seam:** Find a place to break dependencies.
2.  **Break Dependency:** Isolate the class/function.
3.  **Write Characterization Test:** Write a test that asserts the _current_ behavior (even buggy).
4.  **Refactor:** Now you are safe.

---

## Appendix E: The Toolchain

We standardize on a specific toolchain to enforce this manifesto.

1.  **Language:** Python 3.10+ (Type Hinting generics).
2.  **Linter:** `Ruff` (Fast, strict). Configuration in `pyproject.toml`.
3.  **Formatter:** `Black` (Uncompromising).
4.  **Type Checker:** `Mypy` (Strict mode).
5.  **Test Runner:** `Pytest` (With `pytest-cov`, `pytest-xdist`).
6.  **Docs:** `MkDocs` (Material Theme). Architectual Decision Records (ADRs) kept in `docs/adr/`.

---

## Final Word

This manifesto is living. It grows as we grow. But its core principles—Integrity, Rigor, Verification—are immutable.

**End of Document.**

---

## Appendix F: The Glossary

Definitions for the vocabulary of the _Antigravity Architectural Council_.

## F.1 Architectural Terms

- **Aggregate:** A cluster of associated objects that are treated as a unit for the purpose of data changes. External references are restricted to the Aggregate Root.
- **Adapter:** A component that bridges the Domain to the outside world (e.g., a Database Adapter, a File System Adapter). Part of the Hexagonal Architecture.
- **Bounded Context:** A semantic boundary within which a particular domain model is defined and applicable. Ideally, a Microservice or a Module maps to a Bounded Context.
- **Command:** A DTO that encapsulates a request to perform an action (e.g., `LoadSimulationCommand`).
- **Dependency Injection (DI):** A technique where an object receives other objects that it depends on, rather than creating them itself. In this project, we primarily use `pytest` fixtures for DI in tests and `__init__` arguments in production.
- **Domain Event:** A DTO that captures a memory of something interesting which affects the domain (e.g., `SimulationAdded`).
- **Domain Model:** An object model of the domain that incorporates both behavior and data.
- **Entity:** An object that is not defined by its attributes, but rather by a thread of continuity and its identity (e.g., a `Simulation` run).
- **Hexagonal Architecture:** (aka Ports and Adapters) An architectural pattern that allows an application to be equally driven by users, programs, automated tests or batch scripts, and to be developed and tested in isolation from its eventual run-time devices and databases.
- **Repository:** An abstraction that mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects.
- **Service Layer:** The layer that defines the job of the software. It orchestrates the domain objects to perform specific user tasks.
- **Unit of Work (UoW):** A pattern that maintains a list of objects affected by a business transaction and coordinates the writing out of changes and the resolution of concurrency problems.
- **Value Object:** An object that describes some characteristic or attribute but has no conceptual identity. It is immutable (e.g., `Ticks`, `CacheSize`).

## F.2 Data Analysis Terms (Pandas/NumPy)

- **BlockManager:** The internal Pandas object that manages column data storage.
- **Broadcasting:** The ability of NumPy to treat arrays with different shapes during arithmetic operations.
- **Categorical:** A Pandas data type for efficient storage of string data with low cardinality.
- **Continuous Array:** An array stored in a single contiguous block of memory. Necessary for C-level optimization.
- **DataFrame:** A 2-dimensional labeled data structure with columns of potentially different types.
- **Downcasting:** Converting a data type to a smaller representation (e.g., `float64` to `float32`) to save memory.
- **Index:** The labels for the rows of a DataFrame/Series. Can be hierarchical (MultiIndex).
- **Long Format:** A data layout where each row is an observation and each column is a variable. Preferred for analysis.
- **Memory Mapping (`mmap`):** A mechanism to map a file on disk to a range of addresses in the application's process address space, allowing massive arrays to be accessed as if they were in RAM.
- **Series:** A 1-dimensional labeled array.
- **Split-Apply-Combine:** A strategy for data analysis involving splitting the data into groups, applying a function to each group, and combining the results.
- **Strides:** A tuple of bytes to step in each dimension when traversing an array.
- **Vectorization:** Applying operations to entire arrays at once instead of individual elements, typically leveraging SIMD instructions.
- **View:** A slice of an array that shares the same data buffer as the original. Modifying the view modifies the original.
- **Wide Format:** A data layout where data is spread across multiple columns (e.g., `Core0_IPC`, `Core1_IPC`). Preferred for some visualizations but generally avoided in intermediate steps.

## F.3 Testing Terms (TDD/Pytest)

- **Chicago School:** A TDD style that emphasizes testing state and using real objects (or Fakes) rather than Mocks. Focuses on resilience to refactoring.
- **Fixture:** A function decorated with `@pytest.fixture` that provides a fixed baseline (environment, data) for tests.
- **London School:** A TDD style that emphasizes testing interactions (`mock.assert_called_with`). Focuses on isolation and design of interfaces.
- **Mock:** A test double that registers calls made to it and can verify them.
- **Fake:** A test double that has a working implementation but takes shortcuts (e.g., In-Memory Database).
- **Parametrization:** A Pytest feature to run the same test function with multiple sets of arguments.
- **Property-Based Testing:** A testing technique (e.g., `Hypothesis`) where the test framework generates random inputs to verify properties of the output.
- **Test Pyramid:** A heuristic for test distribution: Many Unit Tests, fewer Integration Tests, very few End-to-End tests.

## F.4 Gem5/Research Terms

- **Benchmark:** A specific program run on the simulator (e.g., `gcc`, `gzip`, `mcf`).
- **Config:** The parameter set defining the simulated hardware (e.g., Cache Latency, ROB Size).
- **Core:** A simulated CPU.
- **IPC (Instructions Per Cycle):** The primary metric of CPU performance.
- **ROI (Region of Interest):** The part of the benchmark execution that matters (excluding boot and initialization).
- **SimPoint:** A representative slice of execution used to estimate full-program behavior.
- **Stats:** The output file (`stats.txt`) generated by Gem5 containing hierarchical counters.
- **Tick:** The fundamental unit of time in Gem5 (usually picoseconds).
- **Warmup:** The period of simulation execution used to fill caches before measurements begin.

## F.5 General Engineering Terms

- **Anti-Pattern:** A common response to a recurring problem that is usually ineffective and risks being highly counterproductive.
- **Big Ball of Mud:** A software system that lacks a perceivable architecture.
- **Coupling:** The degree of interdependence between software modules; a measure of how closely connected two routines or modules are; the strength of the relationships between modules.
- **Cyclomatic Complexity:** A quantitative measure of the number of linearly independent paths through a program's source code.
- **Deep Module:** A module with a simple interface but complex functionality (Good).
- **Shallow Module:** A module with a complex interface but simple functionality (Bad).
- **Entropy:** The tendency of a software system to degrade in structure over time.
- **Refactoring:** The process of restructuring existing computer code—changing the factoring—without changing its external behavior.
- **Technical Debt:** The implied cost of future reworking required when choosing an easy but limited solution instead of a better approach that could take longer.

**End of Glossary.**

---

## Appendix G: The Zen of Python (Architecture Edition)

> `import this`

We interpret Tim Peters' aphorisms through the lens of the Antigravity Architecture.

### 1. Beautiful is better than ugly

- **Code:** Use `dataclasses` and type hints.
- **Architecture:** A clear directory structure (`domain/`, `adapters/`) is beautiful. A `utils.py` with 5000 lines is ugly.
- **Gem5:** Parsing logic should read like a grammar, not a regex soup.

### 2. Explicit is better than implicit

- **Code:** `def analyze(simulation: Simulation)` is better than `def analyze(data)`.
- **Architecture:** Use Dependency Injection. Pass the `Repository` explicitly. Don't rely on global `db` objects.
- **Gem5:** If a config value is missing, fail. Don't default to 0.

### 3. Simple is better than complex

- **Code:** Use standard library over heavy dependencies.
- **Architecture:** If a `files.list()` is enough, don't use a Database.
- **Gem5:** Identify the ROI (Region of Interest) simply. Don't use complex heuristic clustering if a 1M cycle window works.

### 4. Complex is better than complicated

- **Code:** A `Simulation` State Machine is complex (many states) but not complicated (easy to follow).
- **Architecture:** The Hexagonal Architecture is complex (many layers) but not complicated (linear dependencies).
- **Gem5:** A Full-System simulation is complex. A script with 50 `if/else` flags is complicated.

### 5. Flat is better than nested

- **Code:** Return early (`guard clauses`). Avoid 5 levels of indentation.
- **Architecture:** Don't have `src/domain/services/impl/analysis/core/cpu.py`. `src/domain/cpu.py` is fine.

### 6. Sparse is better than dense

- **Code:** One class per file if significant. Vertical whitespace is free.
- **Architecture:** Decouple components via Events. Don't wire everything to everything.

### 7. Readability counts

- **Code:** Names matter. `get_l2_miss_rate()` vs `calc()`.
- **Architecture:** The file structure is the table of contents of your system.

### 8. Special cases aren't special enough to break the rules

- **Code:** "I know we shouldn't use globals, but this is just a logger." No. Inject the logger.
- **Architecture:** "This is just a script." No. Put it in `entrypoints/`.

### 9. Although practicality beats purity

- **Code:** Sometimes `pd.read_csv` is faster than a custom parser. Use it (inside an Adapter).
- **Architecture:** Don't use a Message Bus for a "Hello World" app. But RING-5 is not Hello World.

### 10. Errors should never pass silently

- **Code:** `except: pass` is a crime.
- **Architecture:** If `stats.txt` is truncated, the Adapter MUST raise `PartialDataError`.

### 11. Unless explicitly silenced

- **Code:** `with suppress(FileNotFoundError): os.remove(f)`
- **Gem5:** If a specific metric is missing in an old Gem5 version, log a warning and return strict `None`, not 0.

### 12. In the face of ambiguity, refuse the temptation to guess

- **Code:** If `type` is unknown, raise `ValueError`. Don't guess 'O3CPU'.
- **Architecture:** If `config.yaml` is ambiguous, fail startup.

### 13. There should be one-- and preferably only one --obvious way to do it

- **Code:** Use `pytest` for everything. Don't mix `unittest`.
- **Architecture:** There is one way to load data: via the `Loader` adapter. No ad-hoc `open()` calls.

### 14. Although that way may not be obvious at first unless you're Dutch

- **Note:** Hexagonal Architecture is not obvious to Django developers. It takes learning.

### 15. Now is better than never

- **Code:** Write the test now.
- **Architecture:** Refactor the "God Class" now. It will only get worse.

### 16. Although never is often better than _right_ now

- **Code:** Don't deploy on Friday at 5 PM.
- **Architecture:** Don't introduce a Microservice architecture on Day 1.

### 17. If the implementation is hard to explain, it's a bad idea

- **Code:** If you need a paragraph to explain a regex, rewrite it.
- **Architecture:** If you need a whiteboard with 5 colors to explain the data flow, simplify it.

### 18. If the implementation is easy to explain, it may be a good idea

- **Code:** "We split the list, process each chunk, and merge." (MapReduce).
- **Architecture:** "The UI sends a Command, the System updates State, the System emits an Event."

### 19. Namespaces are one honking great idea -- let's do more of those

- **Code:** `import numpy as np`, `import pandas as pd`.
- **Architecture:** `src.domain`, `src.adapters`. Keep boundaries clear.

**End of Document.**
