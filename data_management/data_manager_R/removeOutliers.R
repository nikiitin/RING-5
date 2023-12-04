#!/usr/bin/Rscript

library(readr)
source("utils/util.R")

# Parse arguments
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)
outlierStat <- arguments[currArg]
currArg <- increment(currArg)
nConfigs <- arguments[currArg]
# Until here, arguments are fixed
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)
# Make the config keys to address every config
parsed_data["confKey"] <- ""
parsed_data["confKey"] <- mixStringCols(1, nConfigs, parsed_data)
for (conf in unique(parsed_data[,"confKey"])) {
    for (bench in unique(parsed_data[,"benchmark_name"])) {
        
        dataForOutlier <- parsed_data[parsed_data["benchmark_name"] == bench &
            parsed_data["confKey"] == conf, 
            outlierStat]
        # Calculate quantile and IQR (Using IQR between mean and first element)
        # as we are removing only upper outliers (System calls, page faults etc.)
        Q <- quantile(dataForOutlier, probs=c(0, 0.5), na.rm = FALSE)
        iqr <- Q[2] - Q[1]
        # Set the threshold
        up <-  Q[2] + iqr
        # Filter all data that lies out of the threshold
        parsed_data <- subset(parsed_data, (parsed_data["benchmark_name"] != bench | parsed_data["confKey"] != conf) |
            ((parsed_data["benchmark_name"] == bench & parsed_data["confKey"] == conf) & 
            parsed_data[outlierStat] < up))
    }
}
# Drop configuration keys or seeds reduction will fail
parsed_data["confKey"] <- NULL
# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)