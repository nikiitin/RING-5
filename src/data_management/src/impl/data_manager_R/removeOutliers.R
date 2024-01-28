#!/usr/bin/Rscript

library(readr)
source("src/utils/util.R")

# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
outlier_stat <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
# Until here, arguments are fixed
parsed_data <- read.table(stats_file, sep = " ", header = TRUE)

# Check if random_seed column exists
if (!check_column_exists("random_seed", parsed_data)) {
    stop("random_seed column does not exist. No outliers to remove!")
}
# ConfKey column should already contain benchmark_name and
# configurations
for (conf in unique(parsed_data[, "confKey"])) {
    data_for_outlier <- parsed_data[
        parsed_data["confKey"] == conf,
        outlier_stat
    ]
    # Calculate quantile and IQR (Using IQR between mean and first element)
    # as we are removing only upper outliers (System calls, page faults...)
    q <- quantile(data_for_outlier, probs = c(0, 0.5), na.rm = FALSE)
    iqr <- q[2] - q[1]
    # Set the threshold
    up <- q[2] + iqr
    # Remove outliers by letting only values that lie below the threshold
    # or the ones that are not from the current configuration
    parsed_data <- subset(
        parsed_data,
        (parsed_data["confKey"] != conf) |
            (parsed_data["confKey"] == conf &
                parsed_data[outlier_stat] < up)
    )
}
# Write filtered data onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)