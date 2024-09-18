# Description: This file contains the test cases for the mean configurer.

mean_test_env <- test_env$setup_test_env(test_env, "mean")
# Test case 01 - select one column
test_that("mean", {
  source(paste0(mean_test_env$args_folder, "/01_args_mean_test_simTicks.R"))
  setCommandArgs(args_test_simTicks)
  # Prepare the output file
  file.copy("tests/testthat/mock/mean/test_cases/mean_test_case01.csv",
            "tests/testthat/mock/mean/output/mean_test_case_simTicks.csv",
            overwrite = TRUE)
  # Sourcing the configurer will run it too
  source("src/data_plotter/plot_config/src/configurers/mean/mean.R")
  # Get the result from the output file
  result_csv <- read_data("tests/testthat/mock/mean/output/mean_test_case_simTicks.csv")
  # Get the expected result
  expected_csv <- read_data("tests/testthat/mock/mean/expected_results/mean_test_case_simTicks.csv")
  # Compare the results
  expect_equal(result_csv, expected_csv)
})