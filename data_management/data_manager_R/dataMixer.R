#!/usr/bin/Rscript
library(readr)
source("utils/util.R")
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)

mixingNumber <- arguments[currArg]
currArg <- increment(currArg)
if (mixingNumber == 0) {
  stop("No mixing number specified, skipping this step")
}
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

for (mixing in 1:mixingNumber) {
  newGroupName <- arguments[currArg]
  currArg <- increment(currArg)
  statsToMerge <- arguments[currArg]
  currArg <- increment(currArg)
  # Create a new column for the group
  parsed_data[newGroupName] <- 0
  for(stat in 1:statsToMerge) {
    
    # Add all stats into the column
    mergingStat <- arguments[currArg]
    currArg <- increment(currArg)
    parsed_data[newGroupName] <- parsed_data[newGroupName] + parsed_data[mergingStat]
    
  }
}

# Write everything onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)