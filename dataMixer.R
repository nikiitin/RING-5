#!/usr/bin/Rscript
library(readr)

arguments = commandArgs(trailingOnly = TRUE)
currentArg <- 1
statsFile <- arguments[currentArg]
currentArg <- currentArg + 1

mixingNumber <- arguments[currentArg]
currentArg <- currentArg + 1

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

for (mixing in 1:mixingNumber) {
  newGroupName <- arguments[currentArg]
  currentArg <- currentArg + 1
  statsToMerge <- arguments[currentArg]
  currentArg <- currentArg + 1
  # Create a new column for the group
  parsed_data[newGroupName] <- 0
  for(stat in 1:statsToMerge) {
    
    # Add all stats into the column
    mergingStat <- arguments[currentArg]
    currentArg <- currentArg + 1
    parsed_data[newGroupName] <- parsed_data[newGroupName] + parsed_data[mergingStat]
    
  }
}

# Write everything onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)