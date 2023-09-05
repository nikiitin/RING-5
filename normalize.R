#!/usr/bin/Rscript
library(readr)
source("util.R")
# Parse arguments
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)
normalize <- arguments[currArg]
currArg <- increment(currArg)
sdNorm <- arguments[currArg]
currArg <- increment(currArg)
normalizer_name <- as.numeric(arguments[currArg])
currArg <- increment(currArg)
# Until here all arguments are fixed

if (normalize == "False") {
    stop("Normalize is not set, skipping this step")
}

nStats <- arguments[currArg]
currArg <- increment(currArg)
stats <- NULL

for (stat in 1:nStats) {
    stats <- c(stats, arguments[currArg])
    currArg <- increment(currArg)
}
# Finish argument parsing

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)
# Normalize data

if (normalize == "True") {
  
  # Create new row (sum of all stacked variables)
  parsed_data["total"] <- 0
  for (stat in stats) {
    parsed_data["total"] <- parsed_data["total"] + parsed_data[stat]
  }
  
  for (bench in unique(parsed_data[,"benchmark_name"])){
    dataToNorm <- parsed_data[parsed_data["benchmark_name"] == bench,]
    # It is already ordered, take first element
    normalizer <- dataToNorm[normalizer_name,]
    # Apply normalization
    for (i in 1:length(dataToNorm[,1])) {
      for (stat in stats) {
        stat.sd <- paste("sd", stat, sep=".")
        parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == as.character(dataToNorm[i, "confName"]),stat] <-
            dataToNorm[i,stat] / normalizer["total"] 
        if (sdNorm == "True") {
          parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == as.character(dataToNorm[i, "confName"]),stat.sd] <-
            dataToNorm[i,stat.sd] / normalizer[stat]
        }
      }
    }
  }
}

# Write data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)