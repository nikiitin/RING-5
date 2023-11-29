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
        print("Availables algorithms: mean, geomean")
    } else {
        mean_df <- aggregate(
            parsed_data[(configs+1):ncol(parsed_data)],
            by = parsed_data[1:configs - 1],
            FUN = mean_algorithm)
        mean_df["benchmark_name"] <- "Mean"
    }
    parsed_data <- rbind(parsed_data, mean_df)
} else {
    stop("Mean algorithm not specified, not calculating mean")
}


# Write everything onto csv file
write.table(outputdf, statsFile, sep=" ", row.names = F)