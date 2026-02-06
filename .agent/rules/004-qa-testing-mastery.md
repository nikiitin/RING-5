---
description: QA, Testing, CI/CD, and Property-Based Testing.
globs: tests/**/*.py
---

# 004-qa-testing-mastery.md

## 1. The QA Master

You assume the role of a QA Expert. You know the "Quality Shield" (Test Pyramid) inside out.

## 2. Testing Philosophy (_TDD_ Ch. 1)

### 2.1 The "Why" of Testing

- **Design Tool:** Testing is not just about catching bugs; it is about **Designing** the software. TDD forces loosely coupled, highly cohesive architecture.
- **Documentation:** Tests are the living, executable documentation of the system. "Tests should describe the Architecture."

### 2.2 Core Concepts

- **The TDD Cycle (Red-Green-Refactor):**
  1.  **Red:** Write a failing test for a new requirement (or bug).
  2.  **Green:** Write the _minimum_ code to pass.
  3.  **Refactor:** Clean up while keeping the test passing.
- **Unit Taxonomy:**
  - **Solitary Units:** Test a component in complete isolation (mocks all dependencies). Good for complex algorithmic logic.
  - **Sociable Units:** Test a component with its real functional collaborators (excluding I/O). Good for robust, refactor-friendly tests.
- **Architecture Models:**
  - **Testing Pyramid:** (Base: Unit, Mid: Integration, Tip: E2E). Standard model.
  - **Testing Trophy:** Argues for a larger "Integration" layer (Sociable Tests) to maximize ROI/Confidence. **We prefer Sociable Unit tests** where possible.

### 2.3 Incremental Design (TDD Ch. 3)

- **TODO List:** Maintain a physical list of deferred tasks/missing units while writing high-level tests. Don't implement everything at once.
- **Infinite Loops (REPL):** When testing interactive loops (CLI/Streamlit), run the app in a **Background Thread** or simulate the loop step-by-step.
- **I/O Decoupling:** NEVER call `input()` or `print()` directly in domain logic. Inject `input_func` and `output_func` (or use a `Console` adapter) to enable in-memory verification.

### 2.4 Scaling & Performance (TDD Ch. 4)

- **Testing Buckets:**
  - **Commit Suite:** Runs locally (< 10s). Includes Units + Functional (Fakes).
  - **Nightly Suite:** Runs in CI (> 1min). Includes E2E (Real Network) + Persistence Compatibility.
- **Selection:** Use `-k` or markers (`-m`) to run specific buckets.
- **Performance Tests:** Keep benchmarks in a separate `benchmarks/` directory. NEVER mix them with functional tests.
- **Static Analysis:** Treat Linting (Ruff/MyPy) as the "Compile Step". It MUST pass before tests run.

### 2.5 Pytest Fundamentals (TDD Ch. 5)

- **Fixture-First:** Use fixtures (DI) for setup/teardown. Avoid `setUp`/`tearDown` methods.
- **Yield Fixtures:** Use `yield` for cleanup guarantees (files/DB connections). `code before yield = setup`, `code after yield = teardown`.
- **Scope Discipline:**
  - `function`: Default. Maximum isolation.
  - `session`: Expensive resources (DB, Browser). **Immutable only**.
- **Built-ins:** `tmp_path` (files), `capsys` (stdout), `monkeypatch` (env/attributes).
- **Markers:** Use markers for organization. **CAUTION:** Avoid `autouse=True` unless strictly necessary (hides magic).

### 2.6 Dynamic Configuration (TDD Ch. 6)

- **Fixture Parametrization:** Use `params=[...]` in fixture decorator to run dependent tests multiple times.
- **CLI Options:** Use `pytest_addoption` in `conftest.py` to add flags (e.g., `--run-slow`, `--env=prod`).
- **Introspection:** Use the `request` fixture to access:
  - `request.param`: Current parameter value.
  - `request.config.getoption()`: CLI flags.
  - `request.node.get_closest_marker()`: Test markers.
- **`conftest.py` Hierarchy:** Place general fixtures in root. Place specific overrides in nested `conftest.py`.

### 2.7 Behavior-Driven Development (TDD Ch. 7)

- **Syntax:** Use Gherkin (`Given`, `When`, `Then`) for high-level Acceptance Criteria.
- **Binding:** Use `pytest-bdd` to map Gherkin steps to Python functions.
- **Parameterized Scenarios:** Use `Scenario Outline` + `Examples` table for data-driven acceptance tests.
- **Fixture Reuse:** `@given("step")` steps are essentially Pytest fixtures. Reuse them!

### 2.8 Essential Plugins (TDD Ch. 8)

- **Coverage (`pytest-cov`):** Use `--cov=src --cov-report=term-missing`. Exclude trivial paths with `# pragma: no cover`.
- **Benchmarking (`pytest-benchmark`):** Use `benchmark` fixture. Compare against baselines with `--benchmark-compare`.
- **Parallelism (`pytest-xdist`):** Use `-n auto` for independent tests. **Requirement:** Tests MUST be isolated.
- **Stability (`flaky`):** Use `@flaky` ONLY for external flakiness (Network). Fix logic flakiness immediately.

### 2.9 Environment Management (TDD Ch. 9)

- **Tox:** Use `tox` for automation and isolation.
- **EnvList:** Define separate envs for `py310`, `lint`, and `benchmark`.
- **Consistency:** "If it passes in Tox locally, it should pass in CI."
- **Argument Passing:** Use `{posargs}` in `tox.ini` to allow filtering (e.g., `tox -e py310 -- -k my_test`).

### 2.10 Advanced Quality (TDD Ch. 10)

- **Doctest:** Use `doctest` to ensure documentation examples remain executable and correct.
- **Property-Based Testing (`hypothesis`):** Use for algorithmic invariants.
  - **Invariants:** Round-trip (`enc(dec(x)) == x`), Idempotence (`f(f(x)) == f(x)`), Oracle (`f_new(x) == f_old(x)`).
  - **Shrinking:** Rely on Hypothesis to find minimal failing cases.

### 2.11 Web Integration (TDD Ch. 11)

- **External APIs:** Mock ALL external requests (e.g., `requests-mock`). DO NOT hit real APIs in unit tests.
- **WSGI Testing:** Use `WebTest` or `client` fixtures for fast, in-memory integration testing of web apps.
- **Layering:**
  - **Unit:** Mock network.
  - **Integration:** In-memory stack (WSGI).
  - **E2E:** Real server content (Selenium/Playwright).

### 2.12 End-to-End Automation (TDD Ch. 12)

- **Robot Framework:** Use Keyword-Driven Testing for E2E.
- **Headless CI:** Run browsers in `headless` mode for CI.
- **Artifacts:** Configure auto-screenshots/logs on failure for debugging.
- **Scope:** Limit E2E to critical paths (Smoke Tests).

## 3. Pytest Mastery (_Python Testing with pytest_)

### 3.1 Foundations & Execution (Ch 1 & 2)

- **Discovery Conventions:** Adhere strictly to naming: `test_*.py` for files, `test_*` for functions, and `Test*` for classes (no `__init__`).
- **Knowledge-Building Tests:** Use tests as a "Learning Tool" for new libraries or domain logic. These serve as live documentation.
- **Assertion Mastery:**
  - Use plain Python `assert`. Let `pytest` rewrite and introspect.
  - **AAA Pattern:** Every test must follow **Arrange -> Act -> Assert** structure. No interleaved assertions.
  - **Assertion Helpers:** Extract complex checks into helper functions. Use `__tracebackhide__ = True` inside helpers to focus failure reports on the test call site.
  - **Implicit vs Explicit:** Prefer `assert` for logic; use `pytest.fail("reason")` ONLY for unreachable code paths.
- **Exception Testing:** Use `with pytest.raises(ExpectedException) as exc_info:` to verify failures.
  - Use the `match` parameter with regex to verify error messages.
  - Inspect `exc_info.value` for custom attributes.
- **Outcome Taxonomy:**
  - **FAILED (F):** Logic failure (AssertionError).
  - **ERROR (E):** Infrastructure failure (Fixture error).
  - **XFAIL (x):** Expected Failure. Use for documenting known bugs with `strict=True`.
- **Environment Isolation:** Tests must run in a virtual environment (`venv`) with project-local `pytest` to ensure version consistency across CI and Dev.
- **Verbosity:** Always use `-v` (verbose) and `-vv` (very verbose for complex diffs) during local development to avoid adding `print()` for debugging.

### 3.3 Builtin Fixtures (Ch 4)

- **Temporary Files (`tmp_path`):** Always use `tmp_path` for file I/O tests. It handles unique directory creation and automatic cleanup. Prefer it over legacy `tmpdir`.
- **Output Capture (`capsys`):** Use `capsys` to verify `stdout` and `stderr` for CLI tools. Use `with capsys.disabled()` only for rare real-time debugging.
- **Monkeypatching:** Use the `monkeypatch` fixture to safely replace environment variables, global attributes, or dictionary items during a test. It guarantees automatic restoration.
- **Logging (`caplog`):** Use `caplog` to verify that specific log messages and levels were triggered.
- **Warnings (`recwarn`):** Use `recwarn` for testing that specific `UserWarning` or `DeprecationWarning` are emitted as expected.
- **Metadata (`request`):** Use the `request` fixture within custom fixtures to access metadata about the calling test (e.g., node name, markers).
- **Dependency Injection:** Do not call fixtures directly. Name them as parameters. `pytest` handles the resolution graph.
- **Separation of Concerns:** Keep "Arrange" logic in fixtures. Test functions should focus strictly on "Act" and "Assert".
- **Resource Management:** Use `yield` for resources requiring cleanup (DB, Files). `pytest` guarantees cleanup even on failure.
- **Scoping Strategy:**
  - **Function (Default):** High isolation. Use for data mutation.
  - **Session/Module:** Use for expensive setup (starting simulators, loading 500MB traces).
- **Discoverability:**
  - Use `conftest.py` for sharing. Never import it.
  - Place component-specific fixtures in local `conftest.py` files.
- **Layering:** Build fixtures on top of other fixtures. (e.g., `sim_db` depends on `global_db`).
- **Caution:** Use `autouse=True` sparingly. It hides the "magic" and makes tests harder to reason about for new developers.
- **Introspection:** Use `pytest --fixtures` to audit the project's dependency graph.

### 3.5 Markers & Metadata (Ch 6)

- **Registration:** **ALL** custom markers MUST be registered in `pyproject.toml` or `pytest.ini`. This prevents typos and serves as documentation.
- **Enforcement:** Use `--strict-markers` in `addopts` to turn unknown markers into hard errors.
- **Builtin Markers:**
  - `@pytest.mark.skipif(condition, reason=...)`: Use for platform/version specific tests.
  - `@pytest.mark.xfail(reason=..., strict=True)`: Use for documented bugs. `strict=True` ensures an XPASS becomes a failure, forcing maintenance.
- **Selection:** Use Boolean logic with `-m` (e.g., `smoke or regression`) for flexible test execution.
- **Fixture Integration:** Use `request.node.get_closest_marker("name")` within fixtures to extract configuration from the calling test. This turns markers into powerful "Configuration Hooks".
- **Multi-Level:** markers can be applied to functions, classes, modules (`pytestmark`), or individual parameters.

### 3.6 Test Strategy (Pytest Ch 7)

- **Architecture-Driven:** Focus tests on the **API layer** (Business Logic). Keep CLI/DB as thin "Adapters" with minimal testing.
- **Prioritization Criteria:**
  1.  **Recent:** Code that just changed.
  2.  **Core:** USPs (if these break, no product).
  3.  **Risk:** Complex algorithms, untrusted libs.
  4.  **Problematic:** Frequent regression areas.
  5.  **Expertise:** Single-person-knowledge areas.
- **Methodical Cases:**
  1.  **Happy Path:** Non-trivial standard scenario.
  2.  **Inputs:** Bounds, nulls, large data.
  3.  **States:** Empty, One, Full transitions.
  4.  **Errors:** Invalid IDs, permissions.

### 3.7 Test Doubles Taxonomy (TDD Ch. 2)

- **Dummy:** Passed around but never used (fills parameter lists).
- **Stub:** Provides canned answers (`obj.method.return_value = 5`). Use for query methods.
- **Spy:** key characteristic is behavior tracking (`obj.method.assert_called_once()`). Use for verification.
- **Mock:** Pre-programmed expectations.
- **Fake:** Simpler working implementation (e.g., `InMemoryRepository`). **Prefer Fakes** for databases/stateful systems as they keep tests readable and avoid "mock hell".

### 3.8 Mocking Rules (`unittest.mock`)

- **`patch` vs Injection:** Prefer Dependency Injection (passing mocks in constructor) over `patch` decorators. It makes dependencies explicit.
- **`spec=True`:** ALWAYS use `autospec=True` or `spec=Class` when creating mocks to prevent the "Mocking Non-Existent Method" bug.
- **Boundaries:** Only mock types you _own_. Wrap external 3rd party libraries (like requests/boto3) in a Facade/Adapter, and mock the Adapter.

### 3.9 Configuration Files (Pytest Ch 8)

- **`pyproject.toml`:** The modern standard. Use `[tool.pytest.ini_options]`.
- **Strict Mode:** Set `addopts = "--strict-markers --strict-config -ra"` and `xfail_strict = true` to catch config errors and force bug resolution.
- **`testpaths`:** Explicitly define where tests live to speed discovery.
- **`conftest.py`:** Use for shared fixtures and hooks. Fixtures are scoped to directory. NEVER import `conftest.py` directly.
- **`__init__.py`:** Add to test subdirectories to prevent module name collisions (e.g., `tests/api/test_add.py` vs `tests/cli/test_add.py`).

### 3.10 Code Coverage (Pytest Ch 9)

- **Diagnostic, Not Target:** Coverage % is for finding blind spots. "100% coverage != 0 bugs". Empty assertions still count!
- **Branch Coverage:** Use `--cov-branch` for rigorous testing of `if/else` paths.
- **HTML Reports:** Use `--cov-report=html` to visualize gaps.
- **Exclusions:** Use `# pragma: no cover` for `__main__` blocks and abstract methods. This is a _conscious_ decision, not laziness.
- **CI Threshold:** Use `--cov-fail-under=N` to prevent coverage decay in large projects.

### 3.11 Mocking Deep Dive (Pytest Ch 10)

- **Where to Patch:** Patch where the object is **used**, not where it is **defined**. (e.g., patch `cli.cards.CardsDB`, not `api.CardsDB`).
- **`autospec=True`:** MANDATORY. Prevents "Mock Drift" where mock accepts calls that real object doesn't.
- **`side_effect`:** Use to simulate exceptions for error-handling tests.
- **Refactoring Trap:** Mocks test _Implementation_, not _Behavior_. Prefer real objects with temp DBs for "Integration Lite" tests when possible.

### 3.12 Tox and CI (Pytest Ch 11)

- **Tox Matrix:** Use for testing against multiple Python versions (e.g., `py310, py311`). Catches packaging gaps.
- **`isolated_build = True`:** REQUIRED for modern `pyproject.toml` projects.
- **`skip_missing_interpreters = True`:** Use for local development where not all Pythons are installed.
- **CI Culture:** Merge daily. CI is the "Single Source of Truth". If CI fails, it fails.
- **`passenv`:** Explicitly allow host env vars (e.g., `CI`, `GITHUB_ACTIONS`) into tox.

### 3.13 Scripts and Applications (Pytest Ch 12)

- **Importable Script Pattern:** Use `main()` + `if __name__ == "__main__"` for testability. Avoid `subprocess` for testing.
- **`src` Layout:** Enforce it. Use `pythonpath = src` in config.
- **`requirements.txt` apps:** Use `skipsdist = true` in `tox.ini`. Add `-rrequirements.txt` to deps.

### 3.14 Debugging (Pytest Ch 13)

- **Workflow Flags:**
  - `--lf` (last-failed): Focus on the failure.
  - `-x` (exitfirst): Stop on first failure.
  - `-l` (showlocals): Reveal variable values.
  - `--pdb`: Drop into debugger on failure.
- **Output Control:** `--tb=short` or `--tb=no` for clean summaries.
- **Modern `breakpoint()`:** Use `breakpoint()` in code for precise stops.

### 3.15 Third-Party Plugins (Pytest Ch 14)

- **Parallelism (`pytest-xdist`):** `-n auto`. Requires isolated tests.
- **Randomization (`pytest-randomly`):** Use to find hidden dependencies. Save seed for reproducibility.
- **Flakiness (`pytest-rerunfailures`):** Use sparingly. It buys time, not a fix.
- **Time Freezing (`pytest-freezegun`):** Freeze `datetime.now()` for deterministic time-based logic.

### 3.16 Building Plugins (Pytest Ch 15)

- **Entry Point:** `[project.entry-points.pytest11]` in `pyproject.toml` for auto-discovery.
- **Meta-Testing (`pytester`):** Enable in `conftest.py`. Use `pytester.runpytest()` to test plugin behavior.
- **Versioning:** Always pin minimum `pytest` version in plugin dependencies.

### 3.17 Advanced Parametrization (Pytest Ch 16)

- **Custom IDs:** Use `ids=my_func` or `pytest.param(..., id="label")` for readability.
- **Stacking Decorators:** Multiple `@pytest.mark.parametrize` creates Cartesian Product.
- **Indirect Parametrization:** `indirect=True` passes values to fixtures via `request.param`. For complex setup.
- **Optional Fallback:** `getattr(request, "param", default)` for fixtures that work with or without params.

## 4. Property-Based Testing (_Hypothesis_)

- **Usage:** For critical core logic (parsers, math shapers), uses `hypothesis` to find edge cases.
- **Invariants:** Test for:
  - _Round-Tripping:_ `decode(encode(x)) == x`.
  - _Idempotence:_ `clean(clean(x)) == clean(x)`.
  - _Crash Safety:_ Function should not crash for any generated input.

## 5. CI/CD Readiness

- **Determinism:** Tests must pass in any order (`pytest-randomly`).
- **Speed:** Unit tests should run in milliseconds.
- **Coverage:** Aim for high coverage in Domain Logic.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 004**
