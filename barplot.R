#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)
source("util.R")
arguments = commandArgs(trailingOnly = TRUE)

# Arguments parsing
plot.title <- arguments[1]
plot.statsFile <- arguments[2]
plot.xAxisName <- arguments[3]
plot.yAxisName <- arguments[4]
plot.width <- as.integer(arguments[5])
plot.height <- as.integer(arguments[6])
statsFile <- arguments[7]

currArg <- 8
# Variable arguments start
nStats <-arguments[currArg]
currArg <- increment(currArg)
stat <- NULL
for (i in 1:nStats) {
  stat <- c(stat, arguments[currArg])
  currArg <- increment(currArg)
}
if (nStats > 1) {
  stop("Only one stat can be specified to barplot")
}

legendNames <- NULL
nLegendNames <- arguments[currArg]
currArg <- increment(currArg)
if (nLegendNames > 0) {
  for (i in 1:nLegendNames) {
    legendNames <- c(legendNames, arguments[currArg])
    currArg <- increment(currArg)
  }
}
y_breaks <- NULL
n_breaks <- arguments[currArg]
currArg <- increment(currArg)
if (n_breaks > 0) {
  for (i in 1:n_breaks) {
    y_breaks <- c(y_breaks, arguments[currArg])
    currArg <- increment(currArg)
  }
}
y_limit_top <- as.numeric(arguments[currArg])
currArg <- increment(currArg)
y_limit_bot <- as.numeric(arguments[currArg])
currArg <- increment(currArg)
format <- arguments[currArg]
# Finish arguments parsing

# Start data collection
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

stat.sd <- paste("sd", stat, sep=".")
# To keep the order from the configs and benchmarks, turn them into a factor
parsed_data$confKey <- factor(parsed_data$confKey,
  levels = unique(as.character(parsed_data$confKey)),
  ordered = TRUE)
parsed_data$benchmark_name <- factor(parsed_data$benchmark_name,
  levels = unique(as.character(parsed_data$benchmark_name)),
  ordered = TRUE)
# Basic plot
# Just plot the bar and sd
p <- ggplot(parsed_data, aes(x=benchmark_name, fill=confKey, y=parsed_data[,stat])) +
  geom_bar(stat="identity", position="dodge", color="black") +
  geom_errorbar(aes(ymin=parsed_data[,stat] - parsed_data[,stat.sd], ymax=parsed_data[,stat] + parsed_data[,stat.sd]), width=.2, position=position_dodge(.9))

# Here you can change the theme  
p <- p + theme_hc()
p <- p + theme(axis.text.x = element_text(angle = 30, hjust=1, size=10, face="bold"),
	       axis.text.y = element_text(hjust=1, size=10, face="bold"))
#p <- p + scale_x_discrete(guide = guide_axis(n.dodge = 2))
# Add parameters to the plot
# Legend names
if (nLegendNames != 0) {
  p <- p + scale_fill_brewer(palette = "Set1", labels=legendNames)
} else {
  p <- p + scale_fill_brewer(palette = "Set1")
}
# Breaks
if (n_breaks > 0) {
  y_breaks <- as.numeric(y_breaks)
  p <- p + scale_y_continuous(breaks = y_breaks)
}
# Limits
if (y_limit_top > y_limit_bot) {
    limits <- c(y_limit_bot, y_limit_top)
    p <- p + coord_cartesian(ylim=as.numeric(limits))
}
# Title
if (plot.title != "") {
  p <- p + ggtitle(plot.title)
  # In case you want to modify the style
  #p <- p + theme(plot.title = element_text(family, face, colour, size))
}

# X-axis title
if (plot.xAxisName != "") {
  p <- p + xlab(plot.xAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.x = element_text(family, face, colour, size))
}

# Y-axis title
if (plot.yAxisName != "") {
  p <- p + ylab(plot.yAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.y = element_text(family, face, colour, size))
}

ggsave(paste(c(plot.statsFile, ".", format), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device=format)
