# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select
# Test case 01 args
args_test_simTicks <- c(
  "--args",
  "tests/testthat/mock/mean/output/mean_test_case_simTicks.csv",
  "arithmean",
  "1",
  "simTicks",
  "config_description_abbrev",
  "0",
  "benchmark_name")