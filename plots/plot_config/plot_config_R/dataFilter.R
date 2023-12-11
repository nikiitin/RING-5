#!/usr/bin/Rscript
library(readr)
source("utils/util.R")
# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
# Until here, arguments are fixed

# Benchs filtered
n_bench_filtered <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
bench_filtered <- NULL
if (n_bench_filtered > 0) {
  for (i in 1:n_bench_filtered) {
    bench_filtered <- c(bench_filtered, arguments[curr_arg])
    curr_arg <- increment(curr_arg)
  }
}

# Configs filtered
configs_filtered <- NULL
n_configs_filtered <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
if (n_configs_filtered > 0) {
  for (i in 1:n_configs_filtered) {
    configs_filtered <- c(configs_filtered, arguments[curr_arg])
    curr_arg <- increment(curr_arg)
  }
}
# Finish arguments parsing

# Read data from csv
parsed_data <- read.table(stats_file, sep = " ", header = TRUE)
# Data filtering for benchmarks
for (bench_filter in bench_filtered) {
  parsed_data <- parsed_data[parsed_data["benchmark_name"] != bench_filter, ]
}

# Data filtering for configs
for (config in configs_filtered) {
  # Make a new dataframe with the same columns than parsed_data
  parsed_data <- parsed_data[parsed_data["confKey"] != config, ]
}
# Write filtered data onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)