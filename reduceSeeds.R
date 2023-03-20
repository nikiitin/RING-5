#!/usr/bin/Rscript

library(readr)
source("util.R")

arguments = commandArgs(trailingOnly = TRUE)
statsFile <- arguments[1]
configs <- arguments[2]
configs <- as.numeric(configs)
outlierStat <- arguments[3]
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

# Prepare the csv to be parsed by plotters
# Create configuration names
outputdf <- parsed_data
outputdf["confName"] <- ""
for (var in 1:configs) {
  outputdf["confName"] <- paste(outputdf[, "confName"], outputdf[,var])
}
outputdf["confKey"] <- ""
for (var in 1:configs-1) {
  outputdf["confKey"] <- paste(outputdf[, "confKey"], outputdf[,var])
}
print(unique(outputdf[, "confKey"]))
for (conf in unique(outputdf[, "confKey"])) {
  for (bench in unique(outputdf[, "benchmark_name"])) {
    print(conf)
    print(bench)
    dataForBench <- parsed_data[outputdf["benchmark_name"] == bench & outputdf["confKey"] == conf,
      outlierStat]
    print(dataForBench)
    Q <- quantile(dataForBench, probs=c(0.25, 0.7), na.rm = FALSE)
    iqr <- Q[2] - Q[1]
    up <-  Q[2]+1.5*iqr # Upper Range  (Maybe adjustable?)
    outputdf <- subset(outputdf, 
      (outputdf["benchmark_name"] != bench | outputdf["confKey"] != conf) |
      (outputdf["benchmark_name"] == bench & outputdf["confKey"] == conf & 
       outputdf[outlierStat] < up))
  }
}

# Calculate mean
outputdf <- aggregate(outputdf[(configs+1):ncol(outputdf)], by=outputdf[1:configs],FUN = mean)
outputdf["random_seed"] <- NULL
# Calculate sd
secondOdf <- aggregate(outputdf[(configs+1):ncol(outputdf)], by=outputdf[1:configs],FUN = sd)
secondOdf["random_seed"] <- NULL

# Rename columns to differentiate between mean and sd
colnames(secondOdf)[(configs + 1):ncol(secondOdf)] <- paste("sd", colnames(secondOdf)[(configs + 1):ncol(secondOdf)], sep = "-")

# Merge both df
outputdf <- merge(x=outputdf, y=secondOdf, by = colnames(outputdf)[1:configs])


# Write everything onto csv file
write.table(outputdf, statsFile, sep=" ", row.names = F)