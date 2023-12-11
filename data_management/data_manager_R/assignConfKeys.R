#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]

parsed_data <- read.table(stats_file, sep = " ", header = TRUE)
n_configs <- 0
# Check if random_seed column exists

if (!check_column_exists("benchmark_name", parsed_data)) {
    stop("No benchmarks detected, cannot generate conf keys...")
} else {
    n_configs <- get_column_index("benchmark_name", parsed_data)
}

# Create conf keys for every configuration
conf_keys <- mixStringCols(1, n_configs, parsed_data)
parsed_data <- cbind(confKey = conf_keys, parsed_data)
# Write data frame onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)