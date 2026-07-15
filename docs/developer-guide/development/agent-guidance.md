---
layout: default
title: Repository Guidance
parent: Development
grand_parent: Developer Guide
nav_order: 7
permalink: /developer-guide/development/agent-guidance/
---

# Repository guidance

[`AGENTS.md`](https://github.com/nikiitin/RING-5/blob/main/AGENTS.md) is the authoritative short guide for automated and human
contributors. It defines architecture invariants, the supported public API, commands, extension
points, and the review checklist.

Task recipes under [`.agents/skills/`](https://github.com/nikiitin/RING-5/tree/main/.agents/skills) cover adding a plot, shaper, parser,
or renderer, testing Streamlit with Playwright, and auditing the public API. Read the relevant recipe
before editing the subsystem. Do not copy those instructions into general documentation; link to
them so the contract has one maintained source.

Generated plans, tool state, credentials, and local application data do not belong in commits.
