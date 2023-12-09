#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
outlier_stat <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
n_configs <- arguments[curr_arg]
# Until here, arguments are fixed
parsed_data <- read.table(statsFile, sep = " ", header = TRUE)

# Check if random_seed column exists
if (!check_column_exists("random_seed", parsed_data)) {
    stop("random_seed column does not exist. No outliers to remove!")
}
n_configs <- get_column_index("random_seed", parsed_data)
# Make the config keys to address every configuration
for (conf in unique(parsed_data[, "confKey"])) {
    for (bench in unique(parsed_data[, "benchmark_name"])) {
        data_for_outlier <- parsed_data[parsed_data["benchmark_name"] == bench &
            parsed_data["confKey"] == conf,
            outlierStat]
        # Calculate quantile and IQR (Using IQR between mean and first element)
        # as we are removing only upper outliers (System calls, page faults...)
        q <- quantile(data_for_outlier, probs=c(0, 0.5), na.rm = FALSE)
        iqr <- q[2] - q[1]
        # Set the threshold
        up <-  q[2] + iqr
        # Remove outliers by letting only values that lie below the threshold
        # or the ones that are not from the current configuration
        parsed_data <- subset(parsed_data,
            (parsed_data["benchmark_name"] != bench |
                parsed_data["confKey"] != conf) |
            ((parsed_data["benchmark_name"] == bench &
                parsed_data["confKey"] == conf) &
                parsed_data[outlierStat] < up))
    }
}
# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)