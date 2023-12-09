#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]

parsed_data <- read.table(statsFile, sep = " ", header = TRUE)
n_configs <- 0
# Check if random_seed column exists
if (!check_column_exists("random_seed", parsed_data)) {
    if (!check_column_exists("benchmark_name", parsed_data)) {
        stop("No benchmarks or seeds, cannot generate conf keys...")
    } else {
        n_configs <- get_column_index("benchmark_name", parsed_data)
    }
} else {
    n_configs <- get_column_index("random_seed", parsed_data)
}
# Create conf keys for every configuration
parsed_data["confKey"] <- mixStringCols(1, n_configs, parsed_data)
# Write data frame onto csv file
write.table(parsed_data, statsFile, sep = " ", row.names = FALSE)