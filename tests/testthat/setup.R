# Start a testing environment
library(testthat)
library(readr)
library(Rcpp)
library(withr)
library(rlang)
# Define the test_env variable
# Set the working directory to the main repo directory
setwd(ring_env$root_dir)
source("src/utils/util.R")
test_env <- new.env()
test_env$test_map <- new("MapSet", container_type = "list")

# Define the testing common folders
test_env$mock_folder <- "tests/testthat/mock"
test_env$common_folder <- "tests/testthat/common"
test_env$mock_folder <- "tests/testthat/mock"

test_env$setup_test_env <- function(parent_env, test_module) {
    # Create a copy of the parent environment
    local_env <- env_clone(parent_env)
    # Set the working directory to the main repo directory
    setwd(ring_env$root_dir)
    # Define the folders for the test environment
    local_env$test_cases <-
        paste0(local_env$mock_folder, "/", test_module, "/test_cases")
    local_env$args_folder <-
        paste0(local_env$mock_folder, "/", test_module, "/test_cases/args")
    local_env$output_folder <-
        paste0(local_env$mock_folder, "/", test_module, "/output")
    # emplace at the test_map the test_module with an empty list
    # wich will be the test-cases list
    emplace_element(parent_env$test_map, test_module, list())
    # Return the local environment
    return(local_env)
}

# Source the C++ code to set the command line arguments
sourceCpp(paste0(test_env$common_folder, "/setCommandArgs.cpp"))