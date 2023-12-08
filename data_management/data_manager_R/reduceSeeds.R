#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

arguments <- commandArgs(trailingOnly = TRUE)
stats_file <- arguments[1]
configs <- arguments[2]
configs <- as.numeric(configs)
parsed_data <- read.table(stats_file, sep = " ", header = TRUE)
# Check if random_seed column exists
if (!("random_seed" %in% colnames(parsed_data))) {
    stop("random_seed column does not exist! Not reducing seeds!")
}
seeds_column <- which(colnames(parsed_data) == "random_seed")
# Prepare the csv to be parsed by plotters
# Calculate mean
# All columns from seeds_column to the end should be statistics
# so we should convert them to numeric and do not get any error
# when calculating the mean. Check if the column can be converted
# to numeric, if not, stop the script
if (!all(
    sapply(parsed_data[(seeds_column + 1):ncol(parsed_data)], is.numeric))
) {
    stop("Statistics found not numeric! Not reducing seeds!")
}
# Convert all columns to numeric from seeds_column to the end
parsed_data[(seeds_column + 1):ncol(parsed_data)] <-
    sapply(parsed_data[(seeds_column + 1):ncol(parsed_data)], as.numeric)
# Calculate mean for all statistics
mean_dataframe <- aggregate(
    parsed_data[(seeds_column + 1):ncol(parsed_data)],
    by = parsed_data[1:seeds_column],
    FUN = mean)
mean_dataframe["random_seed"] <- NULL

# Calculate sd for all statistics
sd_dataframe <- aggregate(
    parsed_data[(seeds_column + 1):ncol(parsed_data)],
    by = parsed_data[1:seeds_column],
    FUN = sd)
sd_dataframe["random_seed"] <- NULL
# Rename sd columns to sd-<column_name>
colnames(sd_dataframe)[(seeds_column + 1):ncol(sd_dataframe)] <-
    paste("sd",
    colnames(sd_dataframe)[(seeds_column + 1):ncol(sd_dataframe)],
    sep = "-")

# Merge mean and sd dataframes
outputdf <- merge(x = mean_dataframe,
                  y = sd_dataframe,
                  by = colnames(mean_dataframe)[1:seeds_column])
# Write everything onto csv file
write.table(outputdf, stats_file, sep = " ", row.names = F)