#!/usr/bin/Rscript
library(readr)
source("utils/util.R")
# Parse arguments
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- increment(currArg)
# Until here, arguments are fixed

# Benchs filtered
nBenchFiltered <- arguments[currArg]
currArg <- increment(currArg)
benchFiltered <- NULL
if (nBenchFiltered > 0){
  for (i in 1:nBenchFiltered) {
    benchFiltered <- c(benchFiltered, arguments[currArg])
    currArg <- increment(currArg)
  }
}

# Configs filtered
configsFiltered <- NULL
nConfigsFiltered <- arguments[currArg]
currArg <- increment(currArg)
if (nConfigsFiltered > 0) {
  for (i in 1:nConfigsFiltered) {
    configsFiltered <- c(configsFiltered, arguments[currArg])
    currArg <- increment(currArg)
  }
}
# Finish arguments parsing

# Read data from csv
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)
# Data filtering for benchmarks
for (benchFilter in benchFiltered) {
  parsed_data <- parsed_data[parsed_data["benchmark_name"] != benchFilter,]
}

# Data filtering for configs

for (config in configsFiltered) {
  # Make a new dataframe with the same columns than parsed_data
  parsed_data <- parsed_data[parsed_data["confKey"] != config,]
}
# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)