# Current POM & Test Inventory

> **Purpose**: Quick reference for all existing Page Object Models and test files.
> Updated as new POMs and tests are added.

---

## Page Object Models

| POM                | File                                                                                 | Lines | Properties | Methods | Status                       |
| ------------------ | ------------------------------------------------------------------------------------ | ----: | ---------: | ------: | ---------------------------- |
| `BasePage`         | [tests/visual/pages/base_page.py](tests/visual/pages/base_page.py)                   |   134 |          2 |       9 | ✅ Complete                  |
| `DataSourcePage`   | [tests/visual/pages/data_source_page.py](tests/visual/pages/data_source_page.py)     |   867 |         38 |      42 | ✅ Complete                  |
| `DataManagersPage` | [tests/visual/pages/data_managers_page.py](tests/visual/pages/data_managers_page.py) |   345 |         32 |      24 | ✅ Complete                  |
| `ManagePlotsPage`  | [tests/visual/pages/manage_plots_page.py](tests/visual/pages/manage_plots_page.py)   |    82 |          6 |       5 | ⚠️ Minimal — needs expansion |
| `PerformancePage`  | [tests/visual/pages/performance_page.py](tests/visual/pages/performance_page.py)     |    62 |          4 |       4 | ✅ Adequate                  |
| `PortfolioPage`    | [tests/visual/pages/portfolio_page.py](tests/visual/pages/portfolio_page.py)         |    61 |          5 |       3 | ✅ Adequate                  |

---

## Test Files

| File                                                                  |     Lines | Classes |   Tests | Page Objects Used                                     |   Category |
| --------------------------------------------------------------------- | --------: | ------: | ------: | ----------------------------------------------------- | ---------: |
| [test_ds_rendering.py](tests/visual/test_ds_rendering.py)             |       168 |       3 |      20 | `DataSourcePage`                                      |         UI |
| [test_ds_parser_config.py](tests/visual/test_ds_parser_config.py)     |       255 |       5 |      33 | `DataSourcePage`                                      |         UI |
| [test_ds_csv_recent.py](tests/visual/test_ds_csv_recent.py)           |       143 |       3 |      14 | `DataSourcePage`                                      |         UI |
| [test_ds_add_variable.py](tests/visual/test_ds_add_variable.py)       |       165 |       4 |      18 | `DataSourcePage`                                      |         UI |
| [test_ds_screenshots.py](tests/visual/test_ds_screenshots.py)         |       128 |       1 |      10 | `DataSourcePage`                                      | Screenshot |
| [test_data_managers.py](tests/visual/test_data_managers.py)           |       119 |       3 |      11 | `DataManagersPage`                                    |         UI |
| [test_e2e_parse_workflow.py](tests/visual/test_e2e_parse_workflow.py) |       585 |      10 |      31 | `DataSourcePage`, `DataManagersPage`                  |        E2E |
| [test_navigation.py](tests/visual/test_navigation.py)                 |        68 |       1 |       3 | `BasePage`                                            | Navigation |
| [test_remaining_pages.py](tests/visual/test_remaining_pages.py)       |       100 |       3 |       8 | `ManagePlotsPage`, `PerformancePage`, `PortfolioPage` |         UI |
| **TOTAL**                                                             | **1,731** |  **33** | **148** | **6 POMs**                                            |            |

---

## Test Data Inventory

### Synthetic gem5 Stats Files

| Path                                        | Description                  | Use Case              |
| ------------------------------------------- | ---------------------------- | --------------------- |
| `tests/data/synthetic/single/stats.txt`     | Single CPU, scalar variables | Basic scan/parse      |
| `tests/data/synthetic/multi_cpu/stats.txt`  | Multi-CPU indexed variables  | Pattern aggregation   |
| `tests/data/synthetic/histogram/stats.txt`  | Histogram variables          | Distribution parsing  |
| `tests/data/synthetic/multi_dump/stats.txt` | Multiple dump intervals      | Simpoint testing      |
| `tests/data/synthetic/benchmarks/`          | Multi-benchmark directory    | Benchmarks with seeds |

### Mock Data

| Path                                     | Description              |
| ---------------------------------------- | ------------------------ |
| `tests/data/mock/inputs/csv/configurer/` | CSV test cases           |
| `tests/data/mock/config_files/`          | JSON configuration files |
| `tests/data/mock/expects/csv/`           | Expected output CSVs     |

### Real Data (Large)

| Path                               | Description                       |
| ---------------------------------- | --------------------------------- |
| `tests/data/results-micro26-sens/` | MICRO 2026 sensitivity study data |

---

## conftest.py Fixtures

| Fixture                      | Scope              | Purpose                       |
| ---------------------------- | ------------------ | ----------------------------- |
| `_streamlit_port`            | session            | Free TCP port                 |
| `live_server_url`            | session            | Start/stop Streamlit server   |
| `browser_context_args`       | session            | 1280×720, en-US, dark theme   |
| `browser_type_launch_args`   | session            | Headed/slow-mo modes          |
| `screenshot_dir`             | function           | Per-test screenshot directory |
| `_capture_failure_artifacts` | function (autouse) | Screenshot + trace on failure |

### Planned New Fixtures

| Fixture          | Scope     | Purpose                                   |
| ---------------- | --------- | ----------------------------------------- |
| `shared_page`    | **class** | Shared browser tab for consolidated tests |
| `page_with_data` | **class** | Pre-parsed data for Manage Plots tests    |
