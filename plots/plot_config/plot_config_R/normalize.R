#!/usr/bin/Rscript
library(readr)
source("utils/util.R")
# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
normalize <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
sd_norm <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
normalizer_name <- as.numeric(arguments[curr_arg])
curr_arg <- increment(curr_arg)
# Until here all arguments are fixed

if (normalize == "False") {
    stop("Normalize is not set, skipping this step")
}

n_stats <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
stats <- NULL

for (stat in 1:n_stats) {
    stats <- c(stats, arguments[curr_arg])
    curr_arg <- increment(curr_arg)
}
# Finish argument parsing

parsed_data <- read.table(stats_file, sep = " ", header=TRUE)
# Normalize data

if (normalize == "True") {

  # Create new row (sum of all stacked variables)
  parsed_data["total"] <- 0
  for (stat in stats) {
    parsed_data["total"] <- parsed_data["total"] + parsed_data[stat]
  }

  for (bench in unique(parsed_data[, "benchmark_name"])){
    data_to_norm <- parsed_data[parsed_data["benchmark_name"] == bench, ]
    # It is already ordered, take first element
    normalizer <- data_to_norm[normalizer_name, ]
    # Apply normalization
    for (i in seq_len(nrow(data_to_norm))) {
      for (stat in stats) {
        stat_sd <- paste(stat, "sd", sep = ".")
        # Normalize mean
        parsed_data[
          parsed_data["confKey"] == as.character(data_to_norm[i, "confKey"]),
          stat
        ] <- data_to_norm[i, stat] / normalizer["total"]
        # Normalize standard deviation
        if (sd_norm == "True") {
          parsed_data[
            parsed_data["confKey"] == as.character(data_to_norm[i, "confKey"]),
            stat_sd
          ] <- data_to_norm[i, stat_sd] / normalizer[stat]
        }
      }
    }
  }
}

# Write data onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)