# Description: This file contains the test cases for the sort configurer.

sort_test_env <- test_env$setup_test_env(test_env, "sort")
# Test case 01 - select one column
test_that("sort", {
  source(paste0(sort_test_env$args_folder, "/01_args_sort_test_config_abbrev.R"))
  setCommandArgs(args_test_config_abbrev)
  # Prepare the output file
  file.copy("tests/testthat/mock/sort/test_cases/sort_test_case01.csv",
            "tests/testthat/mock/sort/output/sort_test_case_config_abbrev.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/sort/sort.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/sort/output/sort_test_case_config_abbrev.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/sort/expected_results/sort_test_case_config_abbrev.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})