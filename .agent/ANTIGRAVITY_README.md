# Google Antigravity Agent Configuration for RING-5

Welcome to the **Antigravity AI Workspace** configuration for the **RING-5** unified engine. This documentation describes how the AI natively interprets rules, workflows, skills, and Model Context Protocol (MCP) servers locally, optimized directly for data science excellence.

## 🧠 Knowledge Sources

The Antigravity AI agent has been configured adhering to the principles outlined precisely in our core knowledge base documents:

- _Python for Data Analysis_ (McKinney)
- _Streamlit for Data Science_ (Richards)
- _Web App Development Made Simple with Streamlit_ (Moscato)
- _Matplotlib for Python Developers_
- _Interactive Data Visualization with Python_

These have been distilled directly into `.agent/rules/*`.

## 📌 The Architecture Elements

### 1. Rules (Always Active context)

Living inside `.agent/rules/`:

- `000`: Project Identity & Domain details.
- `001`: Core Architecture & SOLID.
- `002`: Data Science, Pandas, & Numpy practices.
- `003`: Engineering, Typing, and Error Handling.
- `004`: Pytest, TDD, QA Strategy.
- `005`: Workspace boundary enforcement.
- **`006`**: Streamlit state, cache, and fragment mastery.
- **`007`**: Matplotlib vectors, Plotly Graph Objects, colorblind-safe publication plots.

_Note: Antigravity automatically indexes and obeys `.agent/rules` globally on an operation-by-operation basis without needing manual prompt passing._

### 2. Workflows & Skills (Targeted Action)

- **Workflows (`.agent/workflows/`)**: Execute repeatable processes (like parsing or adding a new plot type) incrementally. You can trigger them explicitly using slash commands, e.g. `/test-driven-development`.
- **Skills (`.agent/skills/*/SKILL.md`)**: The agent retrieves this memory autonomously when tackling relevant domain problems (e.g. `shaper-pipeline`, `debug-async-parsing`).

### 3. Model Context Protocol (MCP) Integration

Antigravity seamlessly interfaces with MCP servers configured in `.mcp-config.json` to empower deep research tasks:

- **`vale-linter`**: Ensures all analysis strings and reports map to MICRO 2026 academic tones.
- **`fetch` / `context7`**: Dynamic extraction of updated Pandas/Streamlit API documentation.
- **`puppeteer`**: Automated E2E checking for the Streamlit GUI.
- **`sequential-thinking`**: Used when exploring new data pipeline transformations to avoid hallucination.
- **`ring5-workspace`**: Exclusively scopes the agent's file mutation reach to the repository boundaries.

## 🤝 Keeping the Dual-IDE Setup Intact

As detailed in `DUAL_IDE_SETUP.md`:

- We **Never** mix Antigravity setups with the GitHub Copilot ones.
- Legacy `.agent/skills/*.md` structures or `.github/copilot-instructions.md` are deliberately left untouched, making sure the user can switch IDEs with zero conflicts.

---

> **To the User**: To maximize Antigravity's usefulness, always instruct the agent simply and concisely ("Make a new plot", "Refactor the parser") and trust that it will leverage this rulebook and MCP toolchain independently to produce Publication-Quality architectural grade outputs.
