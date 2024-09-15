# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select
# Test case 02 args
args_test_fail_one_column <- c(
  "--args",
  "tests/testthat/mock/selector/output/selector_test_case_select_one_column.csv",
  "1",
  "config_description_abbre")
