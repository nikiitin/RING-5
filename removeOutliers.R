#!/usr/bin/Rscript

library(readr)
source("util.R")

# create detect outlier function
detect_outlier <- function(x) {
    # calculate third quantile
    Quantile3 <- quantile(x, probs=.75)
    # calculate inter quartile range
    # return true or false
    x > Quantile3 # Detect only upper outliers
}

# create remove outlier function
remove_outlier <- function(dataframe,
                            columns=names(dataframe)) {
    # for loop to traverse in columns vector
    for (col in columns) {
        # remove observation if it satisfies outlier function
        dataframe <- dataframe[!detect_outlier(dataframe[[col]]), ]
    }
    print(dataframe)
}

# Parse arguments
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)
outlierStat <- arguments[currArg]
# Until here, arguments are fixed

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)
for (conf in )
for (bench in unique(parsed_data[,"benchmark_name"])) {

    dataForBench <- parsed_data[parsed_data["benchmark_name"] == bench, outlierStat]
    #print(dataForBench)
    Q <- quantile(dataForBench, probs=c(0.5), na.rm = FALSE)
    #print(Q)
    up <-  Q[1] # Upper Range  (Maybe adjustable?)
    #print(up)
    parsed_data <- subset(parsed_data, (parsed_data["benchmark_name"] != bench |
        (parsed_data["benchmark_name"] == bench) & 
         parsed_data[outlierStat] < up))
}
#print(parsed_data)

# Write filtered data onto csv file
#write.table(parsed_data, statsFile, sep=" ", row.names = F)