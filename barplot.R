#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)

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
currArg <- currArg + 1
stat <- arguments[currArg]
currArg <- currArg + 1
legendNames <- NULL
nLegendNames <- arguments[currArg]
currArg <- currArg + 1
if (nLegendNames > 0) {
  for (i in 1:nLegendNames) {
    legendNames <- c(legendNames, arguments[currArg])
    currArg <- currArg + 1
  }
}
# Finish arguments parsing

# Start data collection
parsed_data <- read.table(fileName, sep = " ", header=TRUE)

# To keep the order from the configs, turn them into a factor
parsed_data$confName <- factor(parsed_data$confName, levels = unique(as.character(parsed_data$confName)), ordered = TRUE)

# Basic plot
# Just plot the bar and sd
p <- ggplot(parsed_data, aes(x=benchmark_name, fill=confName, y=parsed_data[,stat])) +
  geom_bar(stat="identity", position="dodge", color="black") +
  geom_errorbar(aes(ymin=parsed_data[,stat] - parsed_data[,stat.sd], ymax=parsed_data[,stat] + parsed_data[,stat.sd]), width=.2, position=position_dodge(.9))

# Here you can change the theme  
p <- p + theme_hc()

# Add parameters to the plot
# Legend names
if (nLegendNames != 0) {
  p <- p + scale_fill_brewer(palette = "Set1", labels=legendNames)
} else {
  p <- p + scale_fill_brewer(palette = "Set1")
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
ggsave(paste(c(plot.fileName, ".jpg"), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device="jpg")
