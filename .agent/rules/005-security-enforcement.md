---
description: Security enforcement, path safety, architecture boundary validation, and prohibited operations.
globs: "**/*.py"
---

# 005-security-enforcement.md

## 1. The Security Guardian

You enforce security at every layer: file paths, user inputs, dependencies, imports, and agent operations. Security is not optional — it is a pre-condition for all work.

## 2. Prohibited Agent Operations (ABSOLUTE)

### 2.1 Git — NEVER

```bash
# ALL of these are STRICTLY FORBIDDEN:
git add|commit|push|pull|checkout|branch|merge|rebase|stash|reset|revert|tag|clone|fetch
# ANY command starting with 'git' is PROHIBITED
```

**Zero exceptions.** Version control is a human-only responsibility.

### 2.2 System-Level Operations — NEVER

```bash
# FORBIDDEN on host:
sudo|apt-get|yum|dnf|brew install  # System package managers
chmod 777|chown                     # Permission escalation
rm -rf /|rm -rf ~                   # Destructive operations
pip install --break-system-packages # System Python pollution
curl|wget ... | bash                # Remote code execution
eval()|exec()                       # Dynamic code execution in production
```

### 2.3 Directory Access — WORKSPACE ONLY

- All file operations MUST stay within the RING-5 workspace directory
- Use `pathlib.Path.resolve()` to canonicalize paths before any I/O
- Validate with `validate_path_within()` for any user-supplied path

## 3. Path Safety (Mandatory for All I/O)

### 3.1 Always Use pathlib

```python
# ✅ CORRECT
from pathlib import Path

def read_stats(stats_path: Path) -> str:
    resolved = stats_path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Stats file not found: {resolved}")
    return resolved.read_text()

# ❌ FORBIDDEN
import os
data = open(os.path.join(dir, file)).read()  # No os.path, no bare open()
```

### 3.2 Path Traversal Prevention

```python
# ✅ Validate user paths
def safe_path(user_input: str, base_dir: Path) -> Path:
    """Resolve and validate path is within allowed directory."""
    resolved = (base_dir / user_input).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise ValueError(f"Path traversal attempt: {user_input}")
    return resolved
```

### 3.3 Filename Sanitization

- Strip `..`, `/`, `\`, null bytes from user-supplied filenames
- Use `sanitize_filename()` from project utilities for all user inputs
- Never construct paths by string concatenation

## 4. Input Sanitization (Streamlit Layer)

### 4.1 All User Inputs Must Be Validated

```python
# ✅ CORRECT — validate in presentation layer before passing to domain
def handle_user_path(raw_input: str) -> Path:
    sanitized = sanitize_filename(raw_input)
    validated = validate_path_within(Path(sanitized), allowed_base)
    return validated

# ❌ WRONG — raw user input reaches domain layer
path = Path(st.text_input("Enter path"))
data = parse_stats(path)  # UNSAFE
```

### 4.2 Regex Input Safety

- Never pass raw user strings to `re.compile()` without escaping
- Use `re.escape()` for literal matching
- Use `sanitize_glob_pattern()` for glob inputs

## 5. Dependency Security

### 5.1 No Untrusted Dependencies

- Only install packages from PyPI or trusted sources
- Pin exact versions in `pyproject.toml` for production deps
- Use `pip-audit` to check for known vulnerabilities
- Review new dependencies before adding them

### 5.2 Import Safety

- Never use `__import__()` or `importlib.import_module()` with user input
- Never use `pickle.load()` on untrusted data
- Never use `yaml.load()` without `Loader=yaml.SafeLoader`

## 6. Architecture Boundary Enforcement

### 6.1 Layer Import Rules (STRICT)

The codebase follows a strict 3-layer architecture. These import rules are **machine-verifiable** and must be checked before any work is declared complete.

| Source Layer                                           | Can Import From                                   | MUST NOT Import From                |
| :----------------------------------------------------- | :------------------------------------------------ | :---------------------------------- |
| **Layer A** (`src/parsing/`, `src/core/models/`)  | `typing`, `pathlib`, `dataclasses`, `abc`, stdlib | `streamlit`, `plotly`, `matplotlib` |
| **Layer B** (`src/core/services/`, `src/core/common/`) | Layer A, stdlib                                   | `streamlit`, UI modules             |
| **Layer C** (`src/web/`)                               | Layer A, Layer B, `streamlit`, `plotly`           | — (can import anything)             |

### 6.2 Automated Boundary Check Commands

Run these commands to validate architecture boundaries:

```bash
# Check for Streamlit imports in core layer (MUST return empty)
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__

# Check for Plotly imports in core parsing/models (MUST return empty)
grep -rn "import plotly\|from plotly" src/parsing/ src/core/models/ --include="*.py" | grep -v __pycache__

# Check for session_state access outside web layer (MUST return empty)
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__

# Check for direct st. calls in domain logic (MUST return empty)
grep -rn "st\.\(error\|warning\|info\|success\|write\)" src/core/ --include="*.py" | grep -v __pycache__
```

**If any of these return results, the boundary is violated and MUST be fixed before proceeding.**

### 6.3 Dangerous Code Patterns to Detect

```bash
# eval/exec usage (FORBIDDEN in production code)
grep -rn "eval(\|exec(" src/ --include="*.py" | grep -v __pycache__ | grep -v test

# Bare except (FORBIDDEN)
grep -rn "except:" src/ --include="*.py" | grep -v __pycache__

# inplace=True (FORBIDDEN for DataFrames)
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__

# pickle.load on potentially untrusted data
grep -rn "pickle\.load\|pickle\.loads" src/ --include="*.py" | grep -v __pycache__

# subprocess with shell=True (HIGH RISK)
grep -rn "shell=True" src/ --include="*.py" | grep -v __pycache__
```

## 7. Secret & Credential Safety

- **NEVER** hardcode API keys, tokens, passwords, or secrets in source code
- Use environment variables for sensitive configuration
- Check for accidental secret exposure:

```bash
grep -rn "password\|secret\|api_key\|token\|credential\|private_key" src/ --include="*.py" | grep -v __pycache__ | grep -v test | grep -v "# "
```

## 8. Pre-Work Security Checklist

Before declaring any task complete, verify:

- [ ] No new `eval()`, `exec()`, `pickle.load()` in production code
- [ ] All user-supplied paths validated with `pathlib` + boundary check
- [ ] No bare `except:` clauses introduced
- [ ] No `inplace=True` on DataFrames
- [ ] No hardcoded secrets or credentials
- [ ] Architecture layer boundaries respected (run boundary check commands)
- [ ] No `subprocess` with `shell=True` unless absolutely necessary and documented

---

**Status:** ✅ Active
**Priority:** CRITICAL
**Acknowledgement:** ✅ **Acknowledged Rule 005**
