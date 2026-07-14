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

`ManagersAPI` validates and runs arithmetic, column mixing, IQR outlier removal, and repeated-run
reduction. Operations accept DataFrames and return new DataFrames. UI components preview a result
before replacing workspace data.

## Data services

`DataServicesAPI` covers the local CSV pool, saved shaper configuration, parser variables,
portfolios, and path-backed application data. File operations validate names and containment before
reading or writing.

## Shapers

`ShapersAPI` exposes registered identifiers and ordered pipeline execution. `PipelineService`
validates the discriminated step configuration and reports the failing step and identifier.

## Parsing and rendering

`SimulationParser` is defined in the parsing layer because simulator backends own its implementation.
Rendering connector contracts live with the rendering layer; core only owns the engine-independent
models and configuration resolver.

Add a protocol method only when a consumer needs it. Update its implementation, facade delegation,
test fake, and focused tests in the same change.
