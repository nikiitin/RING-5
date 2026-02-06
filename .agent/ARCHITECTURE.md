# RING-5 Application Architecture

> **Version:** 2.0 (Unified Architecture)
> **Status:** Active
> **Last Update:** February 2026

## 1. High-Level Overview

RING-5 is a statistical analysis engine for Gem5 simulations. It transforms raw hierarchical statistics into publication-ready visualizations using a strict **Hexagonal Architecture** (Ports & Adapters).

```mermaid
graph TD
    User((User)) <--> UI[Layer C: Streamlit UI]
    UI <--> Facade[BackendFacade]

    subgraph Core Domain [Layer B: Business Logic]
        Facade --> Service[Analysis Services]
        Service --> Shapers[Shaper Pipeline]
        Service --> Repo[AbstractRepository]
        Shapers --> DataFrame[(Pandas DataFrame)]
    end

    subgraph Infrastructure [Layer A: Ingestion]
        Repo --> LegacyParser[Legacy Parser (stats.txt)]
        Repo --> ModernParser[Modern Parser (stats+config)]
        LegacyParser --> FileSys[(File System)]
        ModernParser --> FileSys
    end
```

## 2. Architectural Layers

### Layer A: Data Ingestion (Infrastructure)

- **Responsibility:** Adapting the external world (Gem5 files) to the internal Domain.
- **Key Components:**
  - `Gem5StatsParser` (Strategy Pattern): Handles file parsing.
  - `Repositories`: Abstract access to data.
- **Data Types:** Raw Strings -> Typed DTOs.

### Layer B: The Domain (Business Logic)

- **Responsibility:** The "Brain". Processing data, calculating metrics, filtering.
- **Key Components:**
  - `Simulation`: The core entity representing a run.
  - `Statistic`: A value with context.
  - `Shapers`: Transformation functions (pure).
- **Constraint:** Pure Python/Pandas. No UI dependencies.

### Layer C: Presentation (UI)

- **Responsibility:** Interaction and Visualization.
- **Key Components:**
  - `Streamlit App`: The view.
  - `PlotFactory`: Creates Plotly figures.
- **Constraint:** Humble Object pattern. Delegates all logic to Layer B.

## 3. Key Design Patterns

| Pattern                     | Usage                                                                |
| :-------------------------- | :------------------------------------------------------------------- |
| **Strategy**                | Swapping between Legacy and Modern Parser logic.                     |
| **Facade**                  | `BackendFacade` allows the UI to talk to the complex backend simply. |
| **Chain of Responsibility** | `Shaper` pipelines for transforming dataframes step-by-step.         |
| **Factory**                 | Creating Plots and Parser instances based on configuration.          |
| **Repository**              | Decoupling domain logic from file storage mechanisms.                |

## 4. Data Flow

1.  **Ingest:** Parsers scan directories -> Detect Mode (Legacy/Modern) -> Extract Stats -> Create `Simulation` objects.
2.  **Load:** `BackendFacade` requests data -> Repository loads CSV/Parquet -> Returns `pd.DataFrame`.
3.  **Process:** Data flows through `Shapers` (Filter Rows -> Calculate Derived Metrics -> Normalize).
4.  **Visualize:** Processed DataFrame -> `PlotFactory` -> `go.Figure` -> Render to Streamlit.

## 5. Technology Stack

- **Language:** Python 3.12+ (Strict Typing)
- **Data:** Pandas, NumPy (Vectorized)
- **Viz:** Plotly Graph Objects
- **UI:** Streamlit
- **Testing:** Pytest, Hypothesis

---

**Note:** This architecture emphasizes separation of concerns. The Domain Layer (Lay B) is the most critical asset and must be kept pure.
