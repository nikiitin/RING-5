---
layout: default
title: Command Palette and Shortcuts
parent: Workflows
grand_parent: User Guide
nav_order: 5
permalink: /user-guide/workflows/command-palette/
---

# Use the command palette

<!--
`uman~ring5.workspace.command-palette.documentation~1`

Covers:
- req~ring5.workspace.command-palette~1

-->

The command palette gives you one searchable list of safe workspace actions. It is useful when you
know what you want to do but do not want to hunt through the sidebar.

Open **Command palette** in the sidebar, or press <kbd>Ctrl</kbd>+<kbd>K</kbd> on Windows and Linux
or <kbd>⌘</kbd>+<kbd>K</kbd> on macOS. Type a page, object, or task such as `plot`, `dataset`,
`upload`, or `help`. Choose a result to run it. Press <kbd>Esc</kbd> to close the palette.

## Available shortcuts

| Shortcut | Action |
| --- | --- |
| <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>K</kbd> | Open the command palette. |
| <kbd>/</kbd> | Open and focus workspace search when you are not already typing. |
| <kbd>Alt</kbd>+<kbd>1</kbd> | Open **Data Source**. |
| <kbd>Alt</kbd>+<kbd>2</kbd> | Open **Data Managers**. |
| <kbd>Alt</kbd>+<kbd>3</kbd> | Open **Manage Plots**. |
| <kbd>Alt</kbd>+<kbd>4</kbd> | Open **Save/Load Portfolio**. |
| <kbd>Alt</kbd>+<kbd>5</kbd> | Open **Documentation**. |

The application ignores `/` and page shortcuts while you are typing in an input, editor, or
selector. Browser, operating-system, and assistive-technology shortcuts still take precedence if
they reserve the same key combination.

## Safety boundary

The palette only contains registered actions. It can navigate and focus search; it does not expose
**Clear Data**, **Reset All**, deletion, overwrite, or another destructive operation. Every command
shows its description and shortcut before you run it.

## Python discovery

Scripts can inspect the same registry without executing a web action:

```python
import ring5

with ring5.Session() as session:
    matches = session.search_workspace_commands("plot export")
    for command in matches.commands:
        print(command.command_id, command.title, command.shortcuts)
```

An empty query lists all registered commands. Search is case-insensitive, uses all supplied terms,
and returns explicit totals and truncation information.
