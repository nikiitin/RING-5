---
layout: default
title: Add a Data Manager
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/extension-guides/adding-a-data-manager/
---

# Add a data manager

A data manager changes the shared workspace table. Put the operation and validation in
`src/core/services/managers/`; put preview and confirmation widgets in
`src/web/components/data_managers/`.

## Implement

<!--
`uman~ring5.extension.data-manager.documentation~1`

Covers:
- req~ring5.extension.data-manager~1

-->

1. Add a stateless service method that validates its columns and returns a new DataFrame.
2. Add the method to `ManagersAPI` and its concrete implementation.
3. Add a UI manager derived from the shared data-manager base. Read data through the API, collect
   configuration, and call the service.
4. Store preview output through the preview API. Replace active data only after an explicit
   confirmation.
5. Record a typed operation-history entry with source columns, destination columns, operation, and
   timestamp.
6. Add the manager to the **Data Managers** page without moving validation into the page.

Use a plot shaper instead when the transformation should affect one figure rather than the shared
workspace.

## Test and verify

Test service validation, numerical behavior, caller-data immutability, preview/confirm flow, and
history. Include missing, non-numeric, empty-group, and standard-deviation propagation cases as
applicable.

```bash
make arch-check
python_venv/bin/pytest tests/unit tests/ui_unit -k "manager" -n 0 --no-cov
```
