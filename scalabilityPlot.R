#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)
source("util.R")
arguments = commandArgs(trailingOnly = TRUE)

# Arguments parsing
plot.title <- arguments[1]
plot.fileName <- arguments[2]
plot.xAxisName <- arguments[3]
plot.yAxisName <- arguments[4]
plot.width <- as.integer(arguments[5])
plot.height <- as.integer(arguments[6])
fileName <- arguments[7]
currArg <- 8
# Variable arguments start

n_lines_configs <- as.integer(arguments[currArg])
currArg <- increment(currArg)
n_stats <- as.integer(arguments[currArg])
n_stats <- n_stats - 1
currArg <- increment(currArg)
if (n_stats > 1) {
    stop("Scalability plot not implemented with more than one stat")
}
line_stat <- NULL
for (i in 1:n_stats) {
  line_stat <- c(line_stat, arguments[currArg])
  currArg <- increment(currArg)
}
x_config <- arguments[currArg]
currArg <- increment(currArg)
var_iterate <- arguments[currArg]

lines_names <- NULL
n_lines_names <- arguments[currArg]
currArg <- increment(currArg)
if (n_lines_names > 0) {
  for (i in 1:n_lines_names) {
    lines_names <- c(lines_names, arguments[currArg])
    currArg <- increment(currArg)
  }
}


# Finish arguments parsing

# Start data collection
parsed_data <- read.table(fileName, sep = " ", header=TRUE)

# Prepare Y-axis (pick stats names)
parsed_data["confLine"] <- mixStringCols(1, n_lines_configs, parsed_data)
# To keep the order from the configs, turn them into a factor
parsed_data$confLine <- factor(parsed_data$confKey, levels = unique(as.character(parsed_data$confKey)), ordered = TRUE)
# Do not iterate over duplicates
vars <- unique(parsed_data[,var_iterate])
# Iterate over selected variable
for (var in vars) {
    plot_data <- parsed_data[parsed_data[var_iterate] == var]
p <- ggplot(data=plot_data, aes(x=plot_data[,x_config], y=plot_data[,line_stat], group=plot_data[,"confLine"])) +
    geom_line(aes(color=plot_data[,"confLine"])) +
    geom_point(aes(color=plot_data[,"confLine"]))
    ggsave(paste(c(plot.filename, "_", var, ".jpg"), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device="jpg")
}

