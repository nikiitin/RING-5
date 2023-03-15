#!/usr/bin/Rscript
library(readr)
# Parse arguments
currArg <- 1
statsFile <- arguments[currArg]
currArg <- currArg + 1
# Until here, arguments are fixed

# Benchs filtered
nBenchFiltered <- arguments[currArg]
currArg <- currArg + 1
benchFiltered <- NULL
if (nBenchFiltered > 0){
  for (i in 1:nBenchFiltered) {
    benchFiltered <- c(benchFiltered, arguments[currArg])
    currArg <- currArg + 1
  }
}

# Configs filtered
configsFiltered <- new.env()
nConfigsFiltered <- arguments[currArg]
currArg <- currArg + 1
if (nConfigsFiltered > 0) {
  for (i in 1:nConfigsFiltered) {
    configName <- arguments[currArg]
    currArg <- currArg + 1
    configVal <- arguments[currArg]
    currArg <- currArg + 1
    configsFiltered[[configName]] <- configVal
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
  parsed_data <- parsed_data[parsed_data[name] == configsFiltered[[name]],]
}

# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)