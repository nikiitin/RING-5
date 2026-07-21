---
layout: default
title: Search the Workspace
parent: Workflows
grand_parent: User Guide
nav_order: 6
permalink: /user-guide/workflows/workspace-search/
---

# Search the Workspace

<!--
`uman~ring5.workspace.global-search.documentation~1`

Covers:
- req~ring5.workspace.global-search~1

-->

Use **Search workspace** at the top of the sidebar when you know what you need but not where it
lives. One query searches the current session and the durable resources available to it:

- configured and scanned variables, including aliases, types, and bounded entry names;
- retained datasets, with row and column counts;
- plots and their mappings;
- individual pipeline steps and their configuration terms;
- saved portfolios;
- application navigation commands; and
- published user and developer guides.

Type at least two letters and press Enter. Search is case-insensitive, punctuation in names such as
`system.cpu.ipc` acts as a word boundary, and every entered term must match. Exact titles rank
first, followed by title prefixes, title text, keywords, and descriptions. Ties use a stable order,
so repeating the same search against unchanged workspace state returns the same list.

Each result says what it is before its title—for example, **Dataset · nightly results** or
**Pipeline · IPC plot · step 1: Sort**. Selecting a dataset activates it before opening Data
Managers. Selecting a plot or pipeline opens Manage Plots with its owner selected. Variable,
portfolio, and navigation results open their owning page. Documentation results are direct links
to the exact published guide.

## Understand the bounds

The browser shows at most 12 results at a time. The public API accepts limits from 1 through 100,
queries up to 200 characters, and indexes at most 2,048 entries of each result kind. The response
does not hide these limits: `results_truncated` means more matches exist, while `index_truncated`
means a result kind exceeded its indexing bound. Refine the query when either message appears.

Search is read-only until you select a result. It never loads a dataset merely to index it and does
not inspect table cells, which keeps searches predictable even when retained tables are large.

The same ranked result contract is available to automation:

```python
import ring5

with ring5.Session() as session:
    response = session.search_workspace("ipc sort", limit=20)

for result in response.results:
    print(result.kind, result.title, result.location, result.identifier)
```
