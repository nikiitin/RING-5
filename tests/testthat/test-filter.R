# Description: This file contains the test cases for the filter configurer.

filter_test_env <- test_env$setup_test_env(test_env, "filter")
# Test case 01 - select one column
test_that("filter", {
  source(paste0(filter_test_env$args_folder, "/01_args_filter_test_req_wins.R"))
  setCommandArgs(args_test_req_wins)
  # Prepare the output file
  file.copy("tests/testthat/mock/filter/test_cases/filter_test_case01.csv",
            "tests/testthat/mock/filter/output/filter_test_case_req_wins.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/filter/filter.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/filter/output/filter_test_case_req_wins.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/filter/expected_results/filter_test_case_req_wins.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})