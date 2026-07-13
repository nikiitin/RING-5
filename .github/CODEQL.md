# CodeQL

The weekly and pull-request CodeQL workflow is defined in
[`workflows/codeql.yml`](workflows/codeql.yml). It analyzes Python production code with GitHub's
`security-and-quality` query suite and uploads results to the repository Security tab.

The workflow:

- runs for pushes and pull requests targeting `main`;
- runs every Monday and supports manual dispatch;
- installs the exact project dependencies for import resolution;
- excludes tests, generated data, virtual environments, and documentation through
  [`codeql/codeql-config.yml`](codeql/codeql-config.yml).

Investigate alerts in the Security tab before dismissing them. Suppress a query only when the data
flow and validation boundary have been verified, and document the reason next to the suppression.

To trigger the workflow manually:

```bash
gh workflow run codeql.yml
```

CodeQL complements, but does not replace, the blocking Bandit and `pip-audit` checks in the main CI
workflow.
