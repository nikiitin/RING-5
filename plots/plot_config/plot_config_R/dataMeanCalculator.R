#!/usr/bin/Rscript
library(readr)
source("utils/util.R")

arguments <- commandArgs(trailingOnly = TRUE)
stats_file <- arguments[1]
mean_algorithm <- arguments[2]
parsed_data <- read.table(stats_file, sep = " ", header = TRUE)

# Calculate mean if specified
# Note that this will add a new "benchmark" to the list
# of benchmarks, which is the mean of all benchmarks
# with the same configuration

benchmarks_column <- get_column_index("benchmark_name", parsed_data)
stats_starting_column <- benchmarks_column + 1
selected_columns <- stats_starting_column:ncol(parsed_data)
config_ending_column <- benchmarks_column - 1
if (mean_algorithm != "None") {
    if (mean_algorithm != "arithmean" &&
        mean_algorithm != "geomean") {
        stop(paste("Mean was specified but with unexpected algorithm.",
        "Available algorithms: arithmean, geomean",
        sep = "\n"))
    } else {
        mean_df <- aggregate(
            parsed_data[selected_columns],
            by = parsed_data[2:config_ending_column],
            FUN = mean_algorithm)
        # config_ending_column has changed index as we removed
        # benchmark_name column (at least for mean_df)
        config_ending_column <- config_ending_column - 1
        # TODO: check if row number is the same as the number of
        # configurations removing duplicates
        mean_df["benchmark_name"] <- mean_algorithm
        mean_df["confKey"] <- ""
        for (i in 1:config_ending_column) {
            mean_df$confKey <- paste(mean_df$confKey,
                mean_df[, i],
                sep = "")
        }
        mean_df$confKey <- paste(mean_df$confKey,
            mean_df$benchmark_name,
            sep = "")
    }
    parsed_data <- rbind(parsed_data, mean_df)
} else {
    stop("Mean algorithm was not specified, skipping mean calculation")
}

# Write everything onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)