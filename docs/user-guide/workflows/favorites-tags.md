---
layout: default
title: Organize Favorites and Tags
parent: Workflows
grand_parent: User Guide
nav_order: 7
permalink: /user-guide/workflows/favorites-tags/
---

# Organize favorites and tags

<!--
`uman~ring5.workspace.favorites-tags.documentation~1`

Covers:
- req~ring5.workspace.favorites-tags~1

-->

Use **Favorites & tags** in the sidebar to keep a large analysis workspace understandable. The
organizer covers configured or scanned variables, retained datasets, plots, individual pipeline
steps, and saved portfolios.

1. Choose an artifact type, or leave **Everything** selected.
2. Optionally filter by one or more existing tags and turn on **Favorites only**.
3. Choose an artifact from the bounded result list.
4. Enter comma-separated tags, choose whether it is a favorite, and select **Save organization**.
5. Select **Open selected artifact** to return to the page that owns it.

Every selected filter tag must match. The star and canonical tags appear in the artifact selector,
so the result remains understandable without relying on color.

## Tag rules

Tags are case-insensitive and stored in lower case. Each artifact accepts at most 16 unique tags;
each tag is at most 32 characters and may contain letters, numbers, spaces, underscores, and
hyphens. Empty tags and punctuation such as commas inside a tag are rejected. Submitting no tags
with **Favorite** off removes the metadata record rather than retaining an empty entry.

The organizer indexes at most 2,048 artifacts of each kind and returns at most 100 at a time. It
warns when the workspace exceeds that bound.

## Reuse and persistence

Variable, dataset, plot, and pipeline organization is stored in the workspace configuration. A
saved portfolio carries those records, and restoring it makes them available again whenever the
matching artifacts exist. For example, a dataset tag reappears if that named dataset is recreated
after restore.

Saved-portfolio favorites and tags live in a small atomic local metadata document beside the
portfolio store. This keeps organization durable without modifying or invalidating a portfolio's
integrity signature. Removing a stale portfolio hides its metadata automatically.

Python uses the same validation and filters:

```python
import ring5

with ring5.Session() as session:
    session.set_workspace_artifact_metadata(
        "variable",
        "system.cpu.ipc",
        tags=("nightly", "paper"),
        favorite=True,
    )
    favorites = session.list_workspace_artifacts(
        tags=("paper",),
        favorites_only=True,
    )
```

These methods only organize discoverable targets. They do not create, load, delete, or overwrite
an artifact.
