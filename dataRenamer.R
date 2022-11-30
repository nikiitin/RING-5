#!/usr/bin/Rscript

library(readr)
arguments = commandArgs(trailingOnly = TRUE)
currentArg <- 1
statsFile <- arguments[currentArg]
currentArg <- currentArg + 1
renamingNumber <- arguments[currentArg]
currentArg <- currentArg + 1

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

for (renaming in 1:renamingNumber) {
  # Get the renaming for the stat we are looking for
  oldName <- arguments[currentArg]
  currentArg <- currentArg + 1
  newName <- arguments[currentArg]
  currentArg <- currentArg + 1
  
  # Do the renaming
  colnames(parsed_data)[colnames(parsed_data) == oldName] <- newName
  # Rename sd if there is
  oldName <- paste("sd", oldName, sep = ".")
  newName <- paste("sd", newName, sep = ".")
  colnames(parsed_data)[colnames(parsed_data) == oldName] <- newName
}

# Write everything onto csv file
write.table(parsed_data,"./wresults.csv", sep=" ", row.names = F)