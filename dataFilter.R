#!/usr/bin/Rscript
library(readr)
source("util.R")
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
configsFiltered <- new.env()
nConfigsFiltered <- arguments[currArg]
currArg <- increment(currArg)
if (nConfigsFiltered > 0) {
  for (i in 1:nConfigsFiltered) {
    configName <- arguments[currArg]
    currArg <- increment(currArg)
    n_config_vals <- arguments[currArg]
    currArg <- increment(currArg)
    for (nconf in 1:n_config_vals) {
      configVal <- arguments[currArg]
      configsFiltered[[configName]] <- c(configsFiltered[[configName]], configVal)
      currArg <- increment(currArg)
    }
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

for (name in names(configsFiltered)) {
  # Make a new dataframe with the same columns than parsed_data
  filtered_data <- parsed_data[0, ]
  configs <- configsFiltered[[name]]
  for (config in configs) {
    filtered_data <- rbind(filtered_data, parsed_data[parsed_data[name] == config,])
  }
  # Update parsed_data so every cycle
  # a variable is filtered
  parsed_data <- filtered_data
}
# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)