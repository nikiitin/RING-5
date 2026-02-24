---
description: Guide to creating a rich Domain Model (DDD) with pure Python objects
---

# Domain Modeling Workflow

> **Invoke with**: `/domain-modeling`
> **Purpose**: create a rich, behavior-focused domain model isolated from infrastructure.
> **Prerequisites**: Understand business requirements and "ubiquitous language".

## Overview

This workflow guides you through creating a Domain Model that encapsulates business logic and rules. The model should vary only when business requirements change, not when infrastructure (DB, API) changes.

## Steps

### Step 1: Identify the Domain Language
**Goal**: Define the core "nouns" and "verbs" from the business requirements.

1.  List the key concepts (e.g., `Batch`, `OrderLine`, `Experiment`).
2.  Identify the invariants (rules that must always be true, e.g., "Cannot allocate more than available quantity").

### Step 2: Create Value Objects
**Goal**: Model immutable concepts defined by their data.

1.  Identify concepts with no identity (e.g., `Money`, `Address`, `Dimension`).
2.  Implement using `@dataclass(frozen=True)`.
3.  **Rule**: Two value objects with same fields are equal.

```python
@dataclass(frozen=True)
class OrderLine:
    order_id: str
    sku: str
    qty: int
```

### Step 3: Create Entities
**Goal**: Model objects with identity that changes state over time.

1.  Identify concepts with identity (e.g., `Batch`, `User`).
2.  Implement `__eq__` and `__hash__` based *only* on the unique ID.
3.  Add methods for business logic (the "verbs").

```python
class Batch:
    def __init__(self, ref: str, qty: int):
        self.reference = ref  # Unique ID
        self._purchased_quantity = qty
        self._allocations = set()

    def allocate(self, line: OrderLine):
        if self.can_allocate(line):
            self._allocations.add(line)

    def __eq__(self, other):
        if not isinstance(other, Batch): return False
        return self.reference == other.reference

    def __hash__(self):
        return hash(self.reference)
```

### Step 4: Define Aggregates
**Goal**: Group related objects into consistency boundaries.

1.  Choose a "Root Entity" for each cluster of objects.
2.  **Rule**: External objects can only hold references to the Root Entity.
3.  **Rule**: All changes to the internals must go through the Root Entity's methods to ensure invariants are checked.

### Step 5: Test in "Low Gear"
**Goal**: Verify domain logic with fast, in-memory unit tests.

1.  Write tests that instantiate domain objects directly.
2.  Assert on the state changes or return values.
3.  **No mocks**: Use real domain objects.

```python
def test_allocating_reduces_available_quantity():
    batch = Batch("batch-001", qty=20)
    line = OrderLine("order-ref", "sku", 2)

    batch.allocate(line)

    assert batch.available_quantity == 18
```

## Next Steps
-   Once the model is solid, create a **Service Layer** to orchestrate these operations (see `/service-layer-flow`).
