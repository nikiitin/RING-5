#!/usr/bin/Rscript
library(readr)
source("util.R")
# Parse arguments
arguments = commandArgs(trailingOnly = TRUE)
currArg <- 1
statsFile <- arguments[currArg]
currArg <- currArg + 1
# Three types of ordering:
# 0. no ordering, skip this step
# 1, alphabetical order (specify if decreasing or not)
# 2, specific order -> specify the config names in 
# the order you want them
orderingType <- as.integer(arguments[currArg])
currArg <- currArg + 1
# Until here, arguments are fixed

configsOrdering <- NULL
nConfigs <- arguments[currArg]
currArg <- currArg + 1
if (nConfigs > 0) {
  for (i in 1:nConfigs) {
    # Remember that here we are expecting the whole confname
    # in case it is specific order
    if (orderingType == 1) {
        configsOrdering <- c(configsOrdering, as.integer(arguments[currArg]))
    } else {
        configsOrdering <- c(configsOrdering, arguments[currArg])
    }
    currArg <- currArg + 1
  }
}
# Finish argument parsing

parsed_data <- read.table(statsFile, sep = " ", header=TRUE)
# Order benchmarks
# TODO: choose the order you prefer for benchs, like in configs
# Rigth now order by alphabetical order
# Put mean at the end!

parsed_data <- parsed_data[order(parsed_data[,"benchmark_name"], decreasing = FALSE),]
mean_df <- parsed_data[parsed_data["benchmark_name"] != "Mean", ]
names_vector <- unique(as.character(mean_df[,"benchmark_name"]))
names_vector <- c(names_vector, "Mean")

parsed_data[["benchmark_name"]] <- factor(parsed_data[["benchmark_name"]], levels = unique(names_vector))
# Reorder benchmarks to have the mean figure at the end

parsed_data <- parsed_data[order(parsed_data[,"benchmark_name"], decreasing = FALSE),]

if (orderingType == 0) {
    # Write data onto csv file
    write.table(parsed_data, statsFile, sep=" ", row.names = F)
    stop("Skipping stats sort step")
}


# Order configurations as desired
if (length(configsOrdering) < 1) {
    stop("No elements were specified to sort stats")
}

if (orderingType == 1) {
    # Sort by order of variables specified
    for (var in configsOrdering) {
        if (is.integer(parsed_data[,var])) {
            parsed_data[,var] <- 
                as.integer(parsed_data[,var])
            parsed_data <- 
                parsed_data[order(as.integer(parsed_data[,var]), decreasing = FALSE),]
        } else {
            parsed_data <- 
                parsed_data[order(parsed_data[,var], decreasing = FALSE),]
	}
    }
} else if (orderingType == 2) {
    # Here we will sort by confName
    confNames <- parsed_data[,"confKey"]
    parsed_data <-
        parsed_data[order(match(confNames, configsOrdering)),]
} else {
    stop("Unexpected sort type")
}
# Write filtered data onto csv file
write.table(parsed_data, statsFile, sep=" ", row.names = F)
