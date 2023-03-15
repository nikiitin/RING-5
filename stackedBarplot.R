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




normalize <- arguments[currArg]
currArg <- currArg + 1

stackVariables <- NULL
nStackVariables <- arguments[currArg]
currArg <- currArg + 1
if (nStackVariables > 0) {
  for (i in 1:nStackVariables) {
    stackVariables <- c(stackVariables, arguments[currArg])
    currArg <- currArg + 1
  }
} else {
  stop("For stacked barplot you should indicate more than one stacking variable.")
}

groupNames <- NULL
nGroupNames <- arguments[currArg]
currArg <- currArg + 1
if (nGroupNames > 0) {
  for (i in 1:nGroupNames) {
    groupNames <- c(groupNames, arguments[currArg])
    currArg <- currArg + 1
  }
}

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

# In this case we need a new df to obtain the plot we need
datos <- data.frame(config = character(), benchmark=character(), stat=character(), data=numeric(), stringsAsFactors = FALSE)
stackIndex <- 0
for (i in 1:nrow(parsed_data)) {
  currRow <- parsed_data[i,]
  for (var in stackVariables) {
    data <- currRow[[var]]
    if (is.nan(data)) {data = 0}
    datos[nrow(datos) + 1,] = c(
      as.character(currRow[["confName"]]),
      as.character(currRow[["benchmark_name"]]),
      var,
      data)  
  }
}

datos$config <- factor(datos$config, levels = unique(as.character(datos$config)), ordered = TRUE)
datos$benchmark <- factor(datos$benchmark, levels = unique(as.character(datos$benchmark)))
datos$stat <- factor(datos$stat, levels = unique(as.character(datos$stat)))
datos$data <- as.numeric(datos$data)
# Basic plot
# Just plot the bar and sd
p <- ggplot(datos, aes(x=config, fill=stat, y=data)) +
  geom_bar(stat="identity", position="stack") +
  facet_grid(~ benchmark)
  
# Here you can change the theme  
p <- p + theme_hc() +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))

#if(normalize == "True") {
#p <- p + scale_y_continuous(limits = c(0, 2), breaks = seq(0, 2, by = 0.5))
  
#}

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
if (nGroupNames != 0) {
  p <- p + scale_x_discrete(labels=groupNames)
}



ggsave(paste(c(plot.fileName, ".jpg"), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device="jpg")
