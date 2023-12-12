#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

arguments <- commandArgs(trailingOnly = TRUE)
stats_file <- arguments[1]
parsed_data <- read.table(stats_file, sep = " ", header = TRUE)

# Check if random_seed column exists
if (!check_column_exists("random_seed", parsed_data)) {
    stop("random_seed column does not exist! Not reducing seeds!")
}

# All columns from seeds_column to the end, except confKey should
# be statistics so we should convert them to numeric and do not
# get any error when calculating the mean. Check if the column
# can be converted to numeric, if not, stop the script
seeds_column <- get_column_index("random_seed", parsed_data)
stat_starting_column <- seeds_column + 1
config_ending_column <- seeds_column - 1
selected_columns <- (stat_starting_column):ncol(parsed_data)
if (!all(
    sapply(
        parsed_data[, selected_columns],
                is.numeric))
) {
    stop("Statistics found not numeric! Not reducing seeds!")
}

# Convert all selected columns to numeric
parsed_data[, selected_columns] <-
    sapply(parsed_data[, selected_columns], as.numeric)

# Calculate mean for each configuration
mean_dataframe <- aggregate(
    parsed_data[selected_columns],
    by = parsed_data[1:(config_ending_column)],
    FUN = mean
)
# Calculate sd for each configuration
sd_dataframe <- aggregate(
    parsed_data[selected_columns],
    by = parsed_data[1:(config_ending_column)],
    FUN = sd_dropna
)
# stat_starting_column has changed index as we removed
# random_seed column
stat_starting_column <- stat_starting_column - 1
# Rename sd columns to sd-<column_name>
colnames(sd_dataframe)[(stat_starting_column):ncol(sd_dataframe)] <-
    paste(colnames(sd_dataframe)[stat_starting_column:ncol(sd_dataframe)],
    "sd",
    sep = "-")

# Merge mean and sd dataframes
# Random seed column is removed here
outputdf <- merge(x = mean_dataframe,
                  y = sd_dataframe,
                  by = colnames(mean_dataframe)[1:(config_ending_column)])
# Write everything onto csv file
write.table(outputdf, stats_file, sep = " ", row.names = FALSE)