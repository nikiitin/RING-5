---
name: Cosmic Python Architecture (Gem5 Edition)
description: "The definitive guide to applying DDD, TDD, and Robust Analysis methodology to the Gem5 Statistical Analysis Engine. Synthesized from 'Architecture Patterns with Python' and project-specific constraints."
---

# Cosmic Python Architecture: The Gem5 Edition

This skill encapsulates the "Brain" of the project's architecture. It merges rigorous software engineering (Cosmic Python) with the specific needs of scientific data analysis (Gem5).

**Mission**: Build a system that is testable, decoupled, and scientifically rigorous.

## 1. Domain Modeling (The Scientific Core)

The Domain Layer is the sanctuary of business logic. It has **zero dependencies** on infrastructure (Streamlit, Plotly, Filesystem).

### Key Patterns & Application

#### 1.1 Entities (Identity Matters)

- **Concept**: Objects defined by _who_ they are, not just _what_ they contain.
- **Gem5 Application**:
  - `SimulationRun`: Identified by a unique `UUID` or `path_hash`. Even if we re-parse the stats, it's the same run.
  - `Experiment`: A named collection of runs (e.g., "Cache Hierarchy Study 2024").

#### 1.2 Value Objects (Data Matters)

- **Concept**: Immutable objects defined by their attributes.
- **Gem5 Application**:
  - `StatMetric`: `(name="system.cpu.ipc", value=1.4, unit="IPC")`.
  - `ConfigParam`: `(key="l1_size", value="64kB")`.
  - **Rule**: Use `@dataclass(frozen=True)`. Operations (math) return _new_ objects.

#### 1.3 Aggregates (Consistency Boundaries)

- **Concept**: A cluster of objects treated as a single unit for data changes.
- **Gem5 Application**:
  - **The `Experiment` Aggregate**:
    - _Invariant_: All runs in an experiment must represent comparable workloads (e.g., you can't average `spec_gcc` with `spec_mcf`).
    - _Rule_: You cannot add a `SimulationRun` to an `Experiment` if it violates the consistency rules (e.g., different Gem5 version).

#### 1.4 Domain Services (Stateless Logic)

- **Concept**: Logic that belongs to the domain but doesn't fit on a single entity.
- **Gem5 Application**:
  - `NormalizationService.normalize(run, baseline)`: Returns a new set of metrics.
  - `AggregationService.average(runs)`: Returns a synthetic "Metadata" run representing the average.

## 2. Infrastructure Layer (Plumbing)

This layer handles the dirty work of talking to the outside world. It depends on the Domain Layer, never the reverse.

### 2.1 Repository Pattern (Abstract Storage)

- **Goal**: Hide the complexity of file formats (`stats.txt`, `config.ini`, `HDF5`).
- **Interface**:
  ```python
  class AbstractRunRepository(Protocol):
      def get(self, run_id: str) -> SimulationRun: ...
      def list(self, filters: Criteria) -> List[SimulationRun]: ...
  ```
- **Adapter**: `FileSystemRepository`. Scans directories, parses files lazily, caches results.

### 2.2 Unit of Work (Atomic Analysis)

- **Goal**: Ensure a set of analysis steps happens atomically or not at all.
- **Gem5 Application**:
  - _Scenario_: Parsing 50 runs and updating the global cache.
  - `with uow:` block ensures that if parsing run #49 fails, we don't end up with a partial cache state.

## 3. Service Layer (Pipelines)

The "High Gear" entry point. Orchestrates the flow of data from Repository -> Domain -> UI.

- **Responsibility**:
  1.  Receive Primitives (strings, ints) from the Entrypoint (UI/CLI).
  2.  Validate Syntax (is this a valid UUID?).
  3.  Fetch Domain Objects from Repository.
  4.  Call Domain Methods (e.g., `experiment.add_run(run)`).
  5.  Persist changes via UoW.
  6.  Return DTOs (Data Transfer Objects) to the UI.

## 4. Testing Strategy

### 4.1 Low Gear (Domain Tests)

- **Target**: `Metric`, `SimulationRun`, `TransformationService`.
- **Style**: Direct instantiation. No mocks.
- **Speed**: Instant (< 1ms).
- **Goal**: Verify statistical correctness (e.g., "Aggregation does not drop outliers").

### 4.2 High Gear (Service Tests)

- **Target**: `ComparisonService`, `LoaderService`.
- **Style**: Use `FakeRepository` to simulate a filesystem full of stats.
- **Goal**: Verify the _flow_. "Given these files exist, when I ask for a comparison, do I get the right result?"

## 5. Event-Driven Architecture (Advanced)

For decoupled updates (critical for Streamlit responsiveness).

- **Pattern**: Domain Events.
- **Flow**:
  1.  `Repository` finishes parsing a massive file.
  2.  Model emits `StatsLoaded(run_id)`.
  3.  Message Bus dispatches to `UpdateCacheHandler`.
  4.  UI (Streamlit) subscribes to cache updates and re-renders automatically.

## 6. Implementation Rules

1.  **Strict Typing**: Every function signature must have types. Use `TypeVar` for generics.
2.  **No "God Objects"**: Avoid a giant `Gem5Manager` class. Split into `Loader`, `Parser`, `Analyzer`.
3.  **Immutability**: Domain objects should be immutable by default. Science should not change data in place.
