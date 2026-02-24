---
description: Guide to implementing Analysis Pipelines (Service Layer) with UoW and Repository
---

# Analysis Pipeline Workflow (Service Layer)

> **Invoke with**: `/service-layer-flow`
> **Purpose**: Decouple scientific logic from I/O using UoW and Repositories.
> **Context**: Orchestrating Gem5 parsing, aggregation, and plotting.

## Overview

The Service Layer (or "Analysis Pipeline") orchestrates use cases. It fetches valid domain objects (Simulations, Experiments) from a Repository, runs domain logic (aggregation, normalization), and persists results via Unit of Work (UoW).

## Steps

### Step 1: Define Abstract Repository
**Goal**: Decouple file system / database access.

1.  Create `adapters/repository.py`.
2.  Define `AbstractRepository` protocol.
3.  **Gem5 Specific**: Ensure methods return `SimulationRun` or `Experiment` objects, not dictionaries.

```python
class AbstractRunRepository(Protocol):
    def get(self, run_id: str) -> SimulationRun: ...
    def list(self, filters: Dict) -> List[SimulationRun]: ...
```

### Step 2: Define Unit of Work (UoW)
**Goal**: Manage atomic analysis sessions (e.g., "Batch Processing").

1.  Create `service_layer/unit_of_work.py`.
2.  Define `AbstractUnitOfWork` as a Context Manager.
3.  **Role**: In a read-heavy app, `commit()` might mean "save processed results to cache" or "export to CSV".

### Step 3: Implement Analysis Function
**Goal**: Orchestrate a single scientific use case.

1.  Create `service_layer/services.py`.
2.  Define a function (e.g., `compare_runs`) that takes primitives as input.
3.  **Pattern**:
    ```python
    def compare_runs(baseline_id: str, target_ids: List[str], uow: AbstractUnitOfWork) -> ComparisonResult:
        with uow:
            baseline = uow.runs.get(baseline_id)
            targets = [uow.runs.get(t_id) for t_id in target_ids]

            # Domain Service Call
            result = comparator.compare(baseline, targets)

            uow.commit() # Save result to cache if needed
            return result
    ```

### Step 4: Test in "High Gear"
**Goal**: Test analysis pipelines with fast fakes.

1.  Create `FakeRunRepository` (loads from a dict of `SimulationRun` objects).
2.  Write tests against the *Service Function*.

```python
def test_compare_runs_logic():
    uow = FakeUnitOfWork()
    uow.runs.add(SimulationRun("base", {"ipc": Metric("ipc", 1.0, "IPC")}))
    uow.runs.add(SimulationRun("test", {"ipc": Metric("ipc", 2.0, "IPC")}))

    result = services.compare_runs("base", ["test"], uow)

    assert result.speedup == 2.0
```

## Next Steps
-   Wire up to **Streamlit** (Presentation Layer). The UI should *only* call these service functions, never the domain objects directly.
