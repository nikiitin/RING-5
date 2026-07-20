---
layout: default
title: Service Protocols
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/api-reference/services-api/
redirect_from:
  - /developer-guide/core/services-reference/
  - /engineering-reference/reference/services-catalog/
---

# Service protocols

Protocol modules under `src/core/services/` define the operations consumed across boundaries.
Concrete implementations compose smaller services; callers depend on the protocol or facade.

## Managers

`ManagersAPI` validates and runs arithmetic, column mixing, IQR outlier removal, repeated-run
reduction, and aligned baseline comparison. Operations accept DataFrames and return new DataFrames.
Comparison requires unique keys in each input and retains unmatched rows with explicit outcomes. UI
components preview a result before replacing workspace data. `compare_statistics` instead treats
rows within each grouping key as repeated samples and returns bounded deterministic inference
results without storing service state.

`annotate_comparison` validates a threshold-comparison result and returns a new DataFrame with
redundant text, shape, and color encodings for improvements, regressions, and tolerated changes.
The UI renders these values and does not reimplement outcome semantics.

`profile_data` calculates duplicate, missing, constant, infinite, IQR-outlier, and expected-type
measurements without mutating the input. It returns immutable records so presentation code cannot
alter the report through a shared DataFrame.

`infer_schema_contract` creates explicit type and nullability defaults from a DataFrame.
`validate_schema` checks required columns, declared types, nullability, numeric bounds, categorical
values, and unexpected columns through `SchemaContractService`. Both operations are stateless and
return immutable models; row evidence is bounded independently of input size.

`DatasetWorkspaceService` provides stateless join and append operations. Session retention and
selection live in `DataRepository`; `ApplicationAPI` coordinates repository reads, manager
operations, and storage of named outputs so the web layer does not compose workspace state itself.
Named-state changes are captured by `DataRepository` as immutable revision snapshots. The facade
adds operation and source labels, while repository-owned fingerprints, parent links, and recovery
stacks keep lineage semantics identical for the web and public Python API.

`DatasetWorkspaceService.diagnose_join` measures duplicate-key rows and groups, unmatched rows, and
matched distinct keys before materialization. `validated_join` enforces pandas-compatible
one-to-one, one-to-many, many-to-one, or explicitly many-to-many relationships and returns the exact
diagnostics used for the decision beside the new DataFrame.

## Data services

<!--
`uman~ring5.data.saved-pipeline-configurations.documentation~1`

Covers:
- req~ring5.data.saved-pipeline-configurations~1

-->

`DataServicesAPI` covers the local CSV pool, saved shaper configuration, parser variables,
portfolios, and path-backed application data. File operations validate names and containment before
reading or writing.

Saved shaper configurations contain a name, description, ordered shaper configuration, and optional
CSV path. The service supports saving, listing, loading, and deleting these path-backed records.

## Shapers

`ShapersAPI` exposes registered identifiers and ordered pipeline execution. `PipelineService`
validates the discriminated step configuration and reports the failing step and identifier.

## Parsing and rendering

`SimulationParser` is defined in the parsing layer because simulator backends own its implementation.
Rendering connector contracts live with the rendering layer; core only owns the engine-independent
models and configuration resolver.

Add a protocol method only when a consumer needs it. Update its implementation, facade delegation,
test fake, and focused tests in the same change.
