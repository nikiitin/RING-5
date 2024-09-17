# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select
# Test case 01 args
args_test_simTicks <- c(
  "--args",
  "tests/testthat/mock/selector/output/selector_test_case_simTicks.csv",
  "4",
  "config_description_abbrev",
  "benchmark_name",
  "random_seed",
  "simTicks")