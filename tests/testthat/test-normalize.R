# Description: This file contains the test cases for the normalize configurer.

normalize_test_env <- test_env$setup_test_env(test_env, "normalize")
# Test case 01 - normalize using simTicks stat
test_that("normalize with simTicks", {
  source(paste0(normalize_test_env$args_folder, "/01_args_normalize_test_simTicks.R"))
  setCommandArgs(args_test_simTicks)
  # Prepare the output file
  file.copy("tests/testthat/mock/normalize/test_cases/normalize_test_case01.csv",
            "tests/testthat/mock/normalize/output/normalize_test_case_simTicks.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/normalize/normalize.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/normalize/output/normalize_test_case_simTicks.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/normalize/expected_results/normalize_test_case_simTicks.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})

# Test case 02 - normalize without specifying any stat
test_that("normalize without specifying stats", {
  source(paste0(normalize_test_env$args_folder, "/02_args_normalize_test_no_stat.R"))
  setCommandArgs(args_test_no_stat)
  # Prepare the output file
  file.copy("tests/testthat/mock/normalize/test_cases/normalize_test_case01.csv",
            "tests/testthat/mock/normalize/output/normalize_test_case_no_stat.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  expect_warning(source("src/data_plotter/plot_config/src/configurers/normalize/normalize.R"),
    "Stats are empty, using all stats. Continuing...")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/normalize/output/normalize_test_case_no_stat.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/normalize/expected_results/normalize_test_case_no_stat.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})