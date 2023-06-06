#!/usr/bin/Rscript
library(readr)
source("util.R")

arguments = commandArgs(trailingOnly = TRUE)
statsFile <- arguments[1]
configs <- arguments[2]
configs <- as.numeric(configs)
mean_algorithm <- arguments[3]
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

# Calculate mean if specified
# Note that this will add a new "benchmark" to the list
if (mean_algorithm != "None") {
    if (mean_algorithm != "mean" &&
        mean_algorithm != "geomean") {
        warning("Mean was specified but with unexpected algorithm")
        print("Available algorithms: mean, geomean")
    } else {
        mean_df <- aggregate(
            parsed_data[(configs + 2):(ncol(parsed_data)-2)],
            by = parsed_data[c(1:configs, ncol(parsed_data))],
            FUN = mean_algorithm)
        mean_df["benchmark_name"] <- "Mean"
    }
    mean_df["confName"] <- mixStringCols(1, configs, mean_df)
    mean_df["confName"] <- paste(mean_df[,"confName"], "Mean", sep="")
    parsed_data <- rbind(parsed_data, mean_df)
}

# Write everything onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)