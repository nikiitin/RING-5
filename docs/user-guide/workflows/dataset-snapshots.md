---
layout: default
title: Reuse Dataset Snapshots
parent: Workflows
grand_parent: User Guide
nav_order: 2.5
permalink: /user-guide/workflows/dataset-snapshots/
---

# Reuse dataset snapshots

<!--
`uman~ring5.data.dataset-snapshots.documentation~1`

Covers:
- req~ring5.data.dataset-snapshots~1

-->

Expand **Reusable dataset snapshots** in **Data Managers → Workspace** after retaining a named
dataset. Choose the dataset, give the snapshot a recognizable name, and select **Save Reusable
Snapshot**. Unlike lineage revisions, reusable snapshots live in the local RING-5 application-data
directory and remain available to later browser and Python sessions. This is useful after an
expensive parse, join, or transformation sequence.

The catalog shows the recorded source name, dimensions, compressed size, and full SHA-256 content
fingerprint. Loading is deliberately a verified operation: **Verify and Load Snapshot** checks both
the stored payload checksum and the fingerprint reconstructed from values, column labels, data
types, and the index before adding anything to the workspace. An incomplete, modified, or
inexactly decodable snapshot is rejected instead of silently returning changed data.

Snapshots use a versioned, compressed, non-executable RING-5 format under
`RING5_DATA_DIR/dataset_snapshots` (or `.ring5/dataset_snapshots` by default). They are local caches,
not signed exchange bundles; use a portable-bundle workflow when sharing artifacts with untrusted
systems. Saving does not overwrite an existing name unless replacement is chosen explicitly.

The public API provides the same lifecycle:

```python
saved = session.save_dataset_snapshot("parsed-and-shaped", "all_runs")
print(saved.fingerprint)

# This can be a new Session in a later process using the same RING5_DATA_DIR.
for snapshot in session.list_dataset_snapshots():
    print(snapshot.name, snapshot.row_count, snapshot.column_count)

session.load_dataset_snapshot(
    "parsed-and-shaped",
    dataset_name="reloaded_runs",
)
session.delete_dataset_snapshot("parsed-and-shaped")
```

When `dataset_name` is omitted during save, the selected named dataset is used; if no named dataset
is selected, the active loaded table is saved as `active_data`. During load, the recorded source
name is the default workspace name. `DatasetSnapshotInfo` contains only immutable metadata and
listing snapshots does not decode their table payloads.
