library(testthat)
library(readr)
library(Rcpp)
# Root RING-5 folder
setwd(ring_env$root_dir)
sourceCpp("tests/testthat/common/setCommandArgs.cpp")

mock_folder <- "tests/testthat/mock/selector/test_cases"
output_mock_folder <- "tests/testthat/mock/selector/output"
# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select

# Test case 01 args
args_test_one_column <- c(
  "--args",
  "tests/testthat/mock/selector/output/selector_test_case_select_one_column.csv",
  "1",
  "config_description_abbrev")


# Test case 01 - select one column
test_that("select one column", {
  setCommandArgs(args_test_one_column)
  # Prepare the output file
  file.copy("tests/testthat/mock/selector/test_cases/selector_test_case01.csv",
            "tests/testthat/mock/selector/output/selector_test_case_select_one_column.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/selector/selector.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/selector/output/selector_test_case_select_one_column.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/selector/expected_results/selector_test_case_select_one_column.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})
