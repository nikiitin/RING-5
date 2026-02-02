# Dependency Update Strategy for RING-5

## 🎯 Overview

This guide explains how to keep RING-5's dependencies up-to-date automatically and safely.

## 🤖 Automated Solutions Implemented

### 1. Dependabot (RECOMMENDED)

**Location**: `.github/dependabot.yml`

**What it does**:

- ✅ Automatically checks for updates weekly (every Monday at 9 AM)
- ✅ Creates individual PRs for security updates
- ✅ Groups minor/patch updates together (reduces PR spam)
- ✅ Separates dev dependencies from production dependencies
- ✅ Automatically updates GitHub Actions versions
- ✅ Runs your CI pipeline for each PR (auto-validates changes)

**Configuration**:

- **Production deps** (pandas, numpy, streamlit, plotly): Grouped together
- **Dev deps** (black, mypy, pytest): Grouped separately
- **Major updates**: Individual PRs (require manual review)
- **PR limit**: 10 open PRs max

**How to use**:

1. Dependabot creates a PR → "deps: Update pandas from 2.3.3 to 2.4.0"
2. GitHub Actions runs automatically (tests, type checking, linting)
3. If ✅ green: Review and merge
4. If ❌ red: Review breaking changes, fix code, merge

**Pros**:

- 🆓 Free for public repos
- 🔄 Fully automated
- 🧪 Auto-tested via CI
- 🔐 Security-focused
- 📧 Email notifications

**Cons**:

- Can create many PRs (mitigated by grouping)
- Major version bumps need manual review

### 2. Dependency Check Workflow

**Location**: `.github/workflows/dependency-check.yml`

**What it does**:

- 📊 Weekly report of outdated packages
- 🔒 Security vulnerability scanning via `pip-audit`
- 📝 Creates GitHub issues when updates are needed
- 📤 Uploads outdated package list as artifact

**Trigger**:

- Automatically: Every Monday at 9 AM UTC
- Manually: GitHub UI → Actions → "Dependency Update Check" → Run workflow

**Output**:

- Summary in Actions tab
- GitHub issue with list of outdated packages
- Downloadable artifact with full details

### 3. Manual Commands (Makefile)

**New commands added**:

```bash
# Check what's outdated
make check-outdated

# Update all dependencies (careful!)
make update-deps

# Security audit
make security-audit

# View dependency tree
make show-deps
```

## 📋 Update Strategy Recommendations

### For Production Dependencies (pandas, numpy, streamlit, plotly)

**Conservative Approach** (RECOMMENDED for RING-5):

```toml
# pyproject.toml
dependencies = [
  "pandas>=2.3.3,<3.0",      # Allow minor updates, block major
  "numpy>=2.4.1,<3.0",
  "streamlit>=1.53.1,<2.0",
  "plotly>=6.5.2,<7.0",
]
```

**Why?**

- Major versions often have breaking changes
- Scientific computing tools (pandas/numpy) need stability
- Publication-quality plots must remain reproducible

### For Dev Tools (black, mypy, flake8, pytest)

**Aggressive Approach**:

```toml
dev = [
  "pytest>=9.0.2",           # Always use latest
  "black>=26.1.0",
  "mypy>=1.13.0",
  "flake8>=7.3.0",
]
```

**Why?**

- Dev tools rarely break your code
- Better type checking and linting over time
- New features improve DX

## 🔄 Recommended Workflow

### Weekly Routine (Automated via Dependabot)

1. **Monday morning**: Dependabot creates PRs
2. **CI runs automatically**: Tests, type checking, linting
3. **You review**:
   - ✅ Green CI + patch/minor update → Merge immediately
   - ⚠️ Green CI + major update → Review changelog, test locally, merge
   - ❌ Red CI → Investigate breaking changes, fix code, merge

### Monthly Routine (Manual Review)

```bash
# 1. Check what's outdated
make check-outdated

# 2. Security audit
make security-audit

# 3. If critical security issues, update immediately:
./python_venv/bin/pip install --upgrade <package>

# 4. Test everything
make test
mypy src/ --strict
black --check src/ tests/
```

## 🚨 When to Update Immediately

**Security Vulnerabilities**:

- `pip-audit` reports CVE → Update ASAP
- Dependabot Security Alert → Update ASAP

**Critical Bugs**:

- Blocker bug in your dependency → Update to patched version

**New Python Version Support**:

- Python 3.13 released → Update dependencies for compatibility

## ⚠️ Caution: Major Version Updates

Before updating to major versions (e.g., pandas 2.x → 3.x):

1. **Read changelog**: Look for breaking changes
2. **Check deprecations**: See what APIs changed
3. **Test locally**:
   ```bash
   ./python_venv/bin/pip install pandas==3.0.0
   make test
   mypy src/ --strict
   ./launch_webapp.sh  # Manual testing
   ```
4. **Create dedicated PR**: Don't mix with other changes
5. **Update documentation**: If APIs changed

## 📊 Monitoring Dashboard

View dependency health:

1. **GitHub Security Tab**: Shows vulnerability alerts
2. **Actions Tab → Dependency Check**: Weekly reports
3. **Dependabot PRs**: Shows pending updates
4. **Issues with `dependencies` label**: Update tracking

## 🔧 Configuration Tuning

### If too many PRs

Edit `.github/dependabot.yml`:

```yaml
open-pull-requests-limit: 5 # Reduce from 10
schedule:
  interval: "monthly" # Reduce frequency
```

### If you want auto-merge for patches

Add to `.github/workflows/`:

```yaml
name: Auto-merge Dependabot
on: pull_request

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-merge patch updates
        if: contains(github.event.pull_request.title, 'deps: Update') && contains(github.event.pull_request.title, 'patch')
        run: gh pr merge --auto --squash "$PR_URL"
```

## 📚 Resources

- [Dependabot docs](https://docs.github.com/en/code-security/dependabot)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Python Package Index](https://pypi.org/)
- [Semantic Versioning](https://semver.org/)

## ✅ Next Steps

1. **Enable Dependabot** (already configured):
   - GitHub repo → Settings → Code security → Enable Dependabot
   - Or just push the `.github/dependabot.yml` file

2. **Test the workflows**:

   ```bash
   # Trigger dependency check manually
   gh workflow run dependency-check.yml
   ```

3. **Review current state**:

   ```bash
   make check-outdated
   make security-audit
   ```

4. **Merge this PR** and let automation handle future updates!
