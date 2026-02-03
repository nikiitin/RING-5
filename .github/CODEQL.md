# CodeQL Security Scanning Setup

This repository uses GitHub's CodeQL for advanced security analysis and vulnerability detection.

## 🔒 What is CodeQL?

CodeQL is GitHub's semantic code analysis engine that treats code as data, allowing you to query code to find security vulnerabilities, bugs, and code quality issues.

## 📋 Current Configuration

### Workflow: `.github/workflows/codeql.yml`

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Weekly schedule (Mondays at 00:00 UTC)
- Manual dispatch

**Analysis:**
- **Language**: Python
- **Query Suite**: `security-and-quality` (includes all default + quality queries)
- **Timeout**: 360 minutes
- **Custom Config**: `.github/codeql/codeql-config.yml`

**Permissions:**
- `security-events: write` - Upload results to Security tab
- `packages: read` - Access CodeQL packs
- `actions: read` - Read workflow runs
- `contents: read` - Read repository content

### Configuration: `.github/codeql/codeql-config.yml`

**Excluded Paths:**
- `tests/data/**` - Test data files (gem5 simulation results)
- `python_venv/**` - Virtual environment
- `**/*.egg-info/**` - Python package metadata
- `**/__pycache__/**` - Python bytecode cache
- `.pytest_cache/**` - Pytest cache
- `docs/**` - Documentation
- `*.md` - Markdown files

## 🚀 Usage

### View Results

1. Go to your repository on GitHub
2. Click the **Security** tab
3. Click **Code scanning alerts** in the sidebar
4. Review any alerts found by CodeQL

### Run Manually

You can trigger a CodeQL scan manually:

```bash
# Via GitHub UI:
Actions → CodeQL Advanced Security → Run workflow

# Or via GitHub CLI:
gh workflow run codeql.yml
```

### Local Testing (Optional)

To run CodeQL queries locally:

```bash
# Install CodeQL CLI
# Download from: https://github.com/github/codeql-cli-binaries/releases

# Create CodeQL database
codeql database create codeql-db --language=python

# Run queries
codeql database analyze codeql-db \
  --format=sarif-latest \
  --output=results.sarif \
  codeql/python-queries:codeql-suites/python-security-and-quality.qls
```

## 🔧 Customization

### Add Custom Queries

Edit `.github/codeql/codeql-config.yml`:

```yaml
queries:
  - name: Custom security queries
    uses: ./my-custom-queries
```

### Fail on Vulnerabilities

To fail CI when high/critical issues are found, uncomment in `codeql.yml`:

```yaml
- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3
  with:
    fail-on: high  # or 'critical'
```

### Filter Specific Queries

In `.github/codeql/codeql-config.yml`:

```yaml
query-filters:
  - include:
      tags contain: security
  - exclude:
      id: py/unused-import
```

## 📊 Query Suites

Available query suites (from least to most queries):

1. **security-extended** - Critical security issues only
2. **security-and-quality** - Security + code quality (current)
3. **code-scanning** - All code scanning queries
4. Custom query packs from CodeQL registry

## 🐛 Common Issues

### False Positives

If CodeQL reports false positives:

1. Review the alert in GitHub Security tab
2. Click "Dismiss alert" and select reason
3. Or add suppression comment in code:
   ```python
   # codeql[py/sql-injection]
   query = f"SELECT * FROM {table}"
   ```

### Performance

If CodeQL times out:
- Increase `timeout-minutes` in workflow
- Exclude more paths in config file
- Use lighter query suite (e.g., `security-extended`)

### Missing Dependencies

If CodeQL can't resolve imports:
- Ensure all dependencies are installed in workflow
- Check `pip install -e ".[dev]"` succeeds
- Add missing packages to `pyproject.toml`

## 📚 Resources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Python Query Reference](https://codeql.github.com/codeql-query-help/python/)
- [Query Suites](https://docs.github.com/en/code-security/code-scanning/managing-your-code-scanning-configuration/codeql-query-suites)
- [Writing Custom Queries](https://codeql.github.com/docs/writing-codeql-queries/codeql-queries/)

## 🔐 Security Best Practices

1. **Review alerts weekly** - Check Security tab regularly
2. **Don't ignore warnings** - Investigate before dismissing
3. **Keep CodeQL updated** - Uses `@v3` for latest features
4. **Enable Dependabot** - Automated dependency updates (already configured)
5. **Use branch protection** - Require CodeQL to pass before merge

## 📝 Recent Fixes

### ReDoS Vulnerability (2026-02-03)
- **File**: `src/web/ui/components/pattern_index_selector.py`
- **Issue**: Catastrophic backtracking in regex pattern
- **Fix**: Simplified `([a-zA-Z_]+[a-zA-Z0-9_]*)` to `([a-zA-Z_]\w*)`
- **Status**: ✅ Resolved

### Type Safety (2026-02-03)
- **File**: `src/parsers/workers/perl_worker_pool.py`
- **Issue**: Optional type not properly narrowed
- **Fix**: Added explicit validation and type annotation
- **Status**: ✅ Resolved

---

**Last Updated**: February 3, 2026
**Maintained by**: RING-5 Development Team
