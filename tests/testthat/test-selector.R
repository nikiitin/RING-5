# Description: This file contains the test cases for the selector configurer.

selector_test_env <- test_env$setup_test_env(test_env, "selector")
# Test case 01 - select one column
test_that("select one column", {
  source(paste0(selector_test_env$args_folder, "/01_args_selector_test_one_column.R"))
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

# Test case 02 - fail select one column that does not exist
test_that("fail select one column", {
  source(paste0(selector_test_env$args_folder, "/02_args_selector_test_fail_one_column.R"))
  setCommandArgs(args_test_fail_one_column)
  # Prepare the output file
  file.copy("tests/testthat/mock/selector/test_cases/selector_test_case01.csv",
            "tests/testthat/mock/selector/output/selector_test_case_fail_select_one_column.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  expect_warning(
    source("src/data_plotter/plot_config/src/configurers/selector/selector.R"),
    "Selected variable is not in the data frame: config_description_abbre")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/selector/output/selector_test_case_fail_select_one_column.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/selector/expected_results/selector_test_case_fail_select_one_column.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})

# Test case 03 - fail select one column that does not exist
test_that("select simTicks", {
  source(paste0(selector_test_env$args_folder, "/03_args_selector_test_simTicks.R"))
  setCommandArgs(args_test_simTicks)
  # Prepare the output file
  file.copy("tests/testthat/mock/selector/test_cases/selector_test_case01.csv",
            "tests/testthat/mock/selector/output/selector_test_case_simTicks.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/selector/selector.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/selector/output/selector_test_case_simTicks.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/selector/expected_results/selector_test_case_simTicks.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})
