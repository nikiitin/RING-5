#!/usr/bin/Rscript
source("util.R")
library(readr)
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)
renamingNumber <- arguments[currArg]
currArg <- increment(currArg)

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

for (renaming in 1:renamingNumber) {
  # Get the renaming for the stat we are looking for
  oldName <- arguments[currArg]
  currArg <- increment(currArg)
  newName <- arguments[currArg]
  currArg <- increment(currArg)
  
  # Do the renaming
  colnames(parsed_data)[colnames(parsed_data) == oldName] <- newName
  # Rename sd if there is
  oldName <- paste("sd", oldName, sep = ".")
  newName <- paste("sd", newName, sep = ".")
  colnames(parsed_data)[colnames(parsed_data) == oldName] <- newName
}

# Write everything onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)