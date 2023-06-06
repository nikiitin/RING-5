#!/usr/bin/Rscript

library(readr)
source("util.R")

arguments = commandArgs(trailingOnly = TRUE)
statsFile <- arguments[1]
configs <- arguments[2]
configs <- as.numeric(configs)
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

# Prepare the csv to be parsed by plotters
# Calculate mean
outputdf <- aggregate(parsed_data[(configs+1):ncol(parsed_data)], by=parsed_data[1:configs],FUN = mean)
outputdf["random_seed"] <- NULL

# Calculate sd
secondOdf <- aggregate(parsed_data[(configs+1):ncol(parsed_data)], by=parsed_data[1:configs],FUN = sd)
secondOdf["random_seed"] <- NULL
# Rename columns to differentiate between mean and sd
colnames(secondOdf)[(configs + 1):ncol(secondOdf)] <- paste("sd", colnames(secondOdf)[(configs + 1):ncol(secondOdf)], sep = "-")

# Merge both df
outputdf <- merge(x = outputdf, y = secondOdf, by = colnames(outputdf)[1:configs])

# Prepare the csv to be parsed by plotters
# Create configuration names
outputdf["confName"] <- mixStringCols(1, configs, outputdf)
outputdf["confKey"] <- mixStringCols(1, configs - 1, outputdf)

# Write everything onto csv file
write.table(outputdf, statsFile, sep=" ", row.names = F)