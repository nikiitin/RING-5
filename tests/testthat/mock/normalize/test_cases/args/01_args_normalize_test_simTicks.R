# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select
# Test case 01 args
args_test_simTicks <- c(
  "--args",
  "tests/testthat/mock/normalize/output/normalize_test_case_simTicks.csv",
  "config_description_abbrev",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrw_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry6_Pflt",
  "1",
  "benchmark_name",
  "1",
  "simTicks",
  "0")