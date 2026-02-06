---
description: Software Engineering, Code Quality, SOLID, and Typing.
globs: src/**/*.py
---

# 003-software-engineering.md

## 1. The Senior Engineer

Your code is robust, readable, type-safe, and secure. You treat Python as a strongly-typed language.

## 2. Strong Typing (Mandatory)

- **Strict Compliance:** All functions, methods, and class attributes **MUST** have type annotations.
- **No `Any`:** Avoid `Any`. Use `TypeVar`, `Protocol` (Structural Typing), or specific types.
- **Collections:** Use `List[str]`, `Dict[str, int]`, not raw `list` or `dict`.
- **Tooling:** Code must pass `mypy --strict`.

## 3. Code Style & Quality

- **Docstrings:** Google Style docstrings for **EVERY** public function/class.
- **Intent over Implementation:** Comments explain _why_, not _what_.
- **No "Thinking" Comments:** Do not leave `# Loop through array` comments.
- **Error Handling:**
  - Catch specific exceptions (`FileNotFoundError`, `KeyError`, `ValueError`).
  - **Fail Fast, Fail Loud:** Raise custom exceptions (`MetricNotFoundError`) immediately if a critical gem5 variable is missing. Do not silently plot 0.
  - Never use bare `except:`.
  - **User Feedback:** Streamlit layer must catch custom domain exceptions and display a friendly `st.error()` while logging the full stack trace to the console.

## 4. SOLID & Architectural Patterns

### 4.1 SOLID Principles

- **SRP (Single Responsibility):** A class should have one reason to change.
  - _Violation:_ `BasePlot` handling both Widget Rendering AND Figure Generation.
- **OCP (Open/Closed):** Add new functionality by adding code, not modifying existing code.
  - _Example:_ Adding a new Plot Type should strictly involve adding a new class file and registering it.
- **LSP (Liskov Substitution):** Subclasses must perfectly mimic the parent interface.
- **ISP (Interface Segregation):** Small, specific interfaces (`IParser`, `IPlotter`) over fat ones.
- **DIP (Dependency Inversion):** Depend on abstractions (`AbstractRepository`), not details (`CsvRepository`).

### 4.2 Patterns from _Architecture Patterns with Python_

- **Domain Modeling (Behavior Over Data):**
  - **Ubiquitous Language:** Code concepts (class names, methods) must strictly match the research domain jargon (e.g., using `ROI` for "Region of Interest", `SKU`, `SimPoint`).
  - **Value Objects:** Represent concepts defined by attributes (e.g., `StatValue`, `Metric`).
    - Implementation: Use `@dataclass(frozen=True)`. Implement value equality (`__eq__`). Immutable by design.
  - **Entities:** Objects with a long-lived unique identity (e.g., `Simulation`, `Batch`).
    - Implementation: `__eq__` and `__hash__` must be based strictly on a unique ID (e.g., `sim_ref`).
  - **Aggregates (Consistency Boundaries):**
    - **Definition:** A cluster of associated objects treated as a single unit for data changes.
    - **Aggregate Root:** The only entry point for modifications (e.g., `Experiment` owns `Simulations`).
    - **Rule:** One Transaction = One Aggregate update. Avoid updating multiple aggregates in a single UoW if possible.
    - **Encapsulation:** Outside code (Service Layer) must only interact with the Aggregate Root. Never hold references to internal entities across transaction boundaries.
    - **One Aggregate = One Repository:** Repositories must strictly return Aggregate Roots.
    - **Concurrency:** Use **Optimistic Concurrency Control** (version numbers) to protect invariants during concurrent writes.
  - **Domain Services:** Logic that doesn't belong to a specific object or involving multiple entities (e.g., `allocate()`, `calculate_speedup()`).
    - Implementation: Prefer **Pure Functions** over "Manager" or "Service" classes to avoid bloat.
  - **Domain Exceptions:** Express business failures (e.g., `OutOfStock`, `MetricNotFoundError`) as custom exception classes. Decouple _what_ failed (Domain) from _how_ to show it (UI).
- **Infrastructure Abstraction (DIP):**
  - **Persistence Ignorance:** The domain model MUST remain a "Plain Old Python Object" (POPO). Avoid database metadata (columns, foreign keys) in domain classes.
  - **Repository Pattern (Port & Adapter):**
    - **Port:** The `AbstractRepository` interface (or Protocol) defining the contract.
    - **Adapter:** Concrete implementations (e.g., `CsvSimulationRepository`, `SqlAlchemyRepository`).
    - **Minimum API:** A repository should ideally only expose `add(entity)` and `get(id)`. Avoid leaking complex SQL/Aggregation logic into the repository interface.
    - **Transaction Boundary:** The Repository handles _collections_, not _transactions_. Do not put `.commit()` inside the repository; leave that to the Unit of Work.
  - **"Don't Mock What You Don't Own":** Never mock complex third-party libraries (e.g., SQLAlchemy Session, Plotly). Instead, **Fake** the abstractions you own (e.g., `FakeRepository`).
    - _Rationale:_ If a Fake is hard to write, your abstraction is likely too complex or poorly defined.
  - **Unit of Work (UoW) - Atomic Integrity:**
    - **Responsibility:** Manages the context of an atomic operation/transaction. Ensures "All or Nothing" persistence.
    - **Implementation:** Use a **Python Context Manager** (`with uow:`).
      - `__enter__`: Starts the transaction/session.
      - `__exit__`: Handles cleanup. Must **Rollback by default** if an exception occurs or if `commit()` wasn't called.
    - **Explicit Commits:** Prefer requiring an explicit `uow.commit()` call. "Explicit is better than implicit."
    - **One Stop Shop:** UoW provides access to Repositories (e.g., `uow.simulations.add(...)`). Do not pass around sessions and repositories separately.
    - **Event Publishing:** The UoW should collect events from "seen" aggregates after a successful commit and pass them to the **Message Bus**.
- **Commands, Events & Message Bus:**
  - **Commands (Intent):** "I want the system to do X" (e.g., `commands.CreateExperiment`).
    - **Grammar:** Imperative mood.
    - **Rules:** Exactly **One Handler**. Must fail **Noisily** (reraise exception to the caller/API).
    - **Validation:** Commands are the primary location for input/intent validation.
  - **Domain Events (Fact):** "X has occurred" (e.g., `events.ExperimentCompleted`).
    - **Grammar:** Past tense.
    - **Rules:** Zero to **N Handlers**. Should fail **Independently** (catch, log, and continue).
    - **Record:** Recorded by the **Aggregate Root** (e.g., `self.events.append(...)`).
  - **Message Bus (Dispatcher):**
    - **Unified Interface:** Treat every use case as a message (Command or Event) to be handled by the bus.
    - **Handlers:** Every handler MUST follow the signature `(message: T, uow: AbstractUnitOfWork)`.
    - **Recursive Processing:** Use a **Queue**. Process the command, then process any resulting events in a loop.
    - **Declarative Logic:** Shift from imperative "do this" to declarative "this happened, react to it."
  - **External Integration (EDA):**
    - **Internal vs External:** Distinguish between **Internal Events** (granular coordination inside the service) and **External Events** (versioned, schema-validated public API contracts for other services).
    - **Temporal Decoupling:** Design for eventual consistency. Assume other systems (e.g., File Storage, External APIs) might be down and use asynchronous messaging where possible.
    - **Correlation IDs:** Every message (Command or Event) SHOULD include a unique `correlation_id` to enable distributed tracing through the entire pipeline.
    - **Adapters:** External inputs (Redis, Webhooks) must be treated as **Entrypoint Adapters** that convert messages into internal **Commands**.
- **CQRS (Command Query Responsibility Segregation):**
  - **Segregation:** Distinguish between **Commands** (Write) and **Queries** (Read).
  - **Write Model (Domain):** Optimized for complex business invariants and consistency boundaries (Aggregates).
  - **Read Model (Queries):** Optimized for performance and presentation. Use Raw SQL, specialized Views, or cache (Redis).
  - **Consistency:** Accept **Eventual Consistency** on the Read side. The UI should be updated via events after the Write model has specialized.
- **Dependency Injection & Bootstrapping:**
  - **Explicit Dependencies:** "Explicit is better than implicit." Pass dependencies (UoW, Adapters) as arguments to handlers/services. Avoid hidden imports that require monkeypatching (`mock.patch`).
  - **Composition Root (`bootstrap.py`):** Maintain a central script responsible for wiring the application together.
    - **Tasks:** Start mappers, initialize adapters, and inject dependencies into handlers.
  - **Metadata-Driven Injection:** Use `inspect.signature` mapping to satisfy handler requirements by argument name. This keeps handler signatures clean while avoiding global state.
  - **Testing:** Use the bootstrapper to override real adapters with **Fakes** during tests (e.g., `bootstrap.bootstrap(uow=FakeUoW())`). This ensures "Patch-less" testing.
- **Service Layer (Orchestration):**
  - **Responsibility:** "Application Logic" (Fetching objects, validating input, calling domain, transaction control), NOT "Business Logic" (rules, math, physics).
  - **Primitives as API:** Service functions should ideally accept primitives (strings, ints, floats) rather than Domain Objects.
    - _Goal:_ Total Decoupling. The caller (UI, CLI) should not need to import `model.py`.
  - **Dependency Injection:** Pass Repositories and Units of Work as arguments (or via a Bootstrap script). This keeps the service layer testable in "High Gear" using Fakes.
  - **Error Mapping:** The service layer is the boundary to convert internal Domain Exceptions (e.g., `model.OutOfStock`) into Application-level errors or UI-friendly notifications.
  - **Entrypoint Layer (UI):** Flask views or Streamlit pages must be "Thin Controllers"—their only job is to extract data from the request and delegate to the Service Layer.
- **Abstractions and Coupling (FCIS):**
  - **Functional Core, Imperative Shell:** Separate decision-making (Pure Logic) from side-effects (I/O).
    - **Functional Core (Domain):** Pure functions/objects that take simple data structures and return them. Infinitely testable without mocks.
    - **Imperative Shell (Adapters/Services):** Gathers I/O, feeds it to the core, and applies changes.
  - **Hoist I/O:** Move disk access and network calls to the extreme edges of the application (Adapters). The "Inner" domain should be "I/O blind."
  - **State over Behavior:** Prefer verifying the _result_ (state) of an operation using Fakes rather than the _process_ (behavior) using Mocks/Spies.
    - _Example:_ Assert a file exists in the `FakeStorage` list rather than asserting `storage.write()` was called with specific arguments.

## 5. TDD & Engineering Excellence

### 5.1 Red-Green-Refactor & Test Pyramid

1.  **Red:** Write a failing test for the Public API (Classicist School). Focus on **Use Cases** (Service Layer) rather than class internals.
2.  **Green:** Write minimal code to pass.
3.  **Refactor:** Apply the **"Rule of Three"**: Extract repeated logic after the third appearance.

### 5.2 Shifting Gears (TDD Strategy)

- **Low Gear (Domain TDD):** Use for new complex features. High feedback for design sketching. These tests are "Sticky Glue"—highly coupled to domain shapes.
- **High Gear (Service TDD):** Use for adding features to stable models and broad refactoring. These tests are the **Workhorse** of the system, covering all edge cases via the Service Layer.
- **Test Setup:** Avoid importing `domain.model` in tests when possible. Use **Application Services** (e.g., `add_batch_service`) to set up state for other tests.
- **Testing Pyramid:**
  - **E2E:** Minimal. One happy/unhappy path per feature.
  - **Service Layer:** The Bulk (80%+). Covers all code paths using Fakes.
  - **Domain Model:** Focused. Verifies complex business math/logic.
- **Cleanup:** Do not be afraid to **Delete Domain Tests** once they are covered by Service Layer tests and the design has stabilized.

### 5.3 Principles of Robustness

- **Idempotence:** Critical operations (e.g., data loading) should be idempotent: `f(f(x)) == f(x)`.
- **Fail Fast, Fail Loud:** Raise `MetricNotFoundError` immediately if data is missing. Do not silently fallback to 0.
- **Crash Safety:** Use `try/except` with specific logging to flag malformed Gem5 lines without terminating the pipeline.

## 6. Security & Safety

- **No Git:** Git commands are strictly forbidden.
- **Path Safety:** Use `pathlib` for all file operations. Validate paths via `path.resolve()` before access.
- **Input Sanitization:** Validate all user inputs from Streamlit before they reach the Domain Layer.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 003**
