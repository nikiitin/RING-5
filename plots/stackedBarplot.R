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

stackVariables <- NULL
nStackVariables <- arguments[currArg]
currArg <- increment(currArg)
if (nStackVariables > 0) {
  for (i in 1:nStackVariables) {
    stackVariables <- c(stackVariables, arguments[currArg])
    currArg <- increment(currArg)
  }
} else {
  stop("For stacked barplot you should indicate more than one stacking variable.")
}

groupNames <- NULL
nGroupNames <- arguments[currArg]
currArg <- increment(currArg)
if (nGroupNames > 0) {
  for (i in 1:nGroupNames) {
    groupNames <- c(groupNames, arguments[currArg])
    currArg <- increment(currArg)
  }
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
currArg <- increment(currArg)
legend_title <- arguments[currArg]
currArg <- increment(currArg)
legend.n_elem_row <- arguments[currArg]
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
      as.character(currRow[["confKey"]]),
      as.character(currRow[["benchmark_name"]]),
      var,
      data)  
  }
}

datos$config <- factor(datos$config, levels = unique(as.character(datos$config)), ordered = TRUE)
datos$benchmark <- factor(datos$benchmark, levels = unique(as.character(datos$benchmark)))
datos$stat <- factor(datos$stat, levels = unique(as.character(datos$stat)))
datos$data <- as.numeric(datos$data)
datos$data <- datos$data * 100
# Basic plot
# Just plot the bar and sd
p <- ggplot(datos, aes(x=benchmark, fill=stat, y=data)) +
  geom_bar(stat="identity", position="stack") #+
  #facet_grid(~ benchmark, switch = "x")
  
# Here you can change the theme
p <- p + theme_hc() +
  theme(axis.text.x = element_text(angle = 30, hjust=1, size=10, face="bold"),
  	axis.text.y = element_text(size=10, face="bold"),
	  strip.text.x = element_text(angle = 45, size=10, face="bold"), strip.placement = "outside",
    strip.background = element_rect(fill = NA, color = "white"),
    panel.spacing = unit(-.01, "cm"), legend.position="top",
    legend.justification="right")

#if(normalize == "True") {
#p <- p + scale_y_continuous(limits = c(0, 2), breaks = seq(0, 2, by = 0.5))
  
#}

# Add parameters to the plot
# Limits
if (y_limit_top > y_limit_bot) {
  if (n_breaks > 0) {
    p <- p + scale_y_continuous(limits = c(y_limit_bot, y_limit_top),
      breaks = y_breaks)
  } else {
    p <- p + scale_y_continuous(limits = c(y_limit_bot, y_limit_top))
  }
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
# Legend names
if (nLegendNames != 0) {
  p <- p + scale_fill_viridis_d(option="plasma", labels=legendNames, direction = -1)
} else {
  p <- p + scale_fill_viridis_d(option="plasma", direction = -1)
}
# Legend title and n elements per row
#Number of elements per row in legend
if (legend.n_elem_row != 0) {
    p <- p + guides(fill=guide_legend(fill=guide_legend(nrow=legend.n_elem_row),title=legend_title))
} else {
    p <- p + guides(fill=guide_legend(title=legend_title))
}
# Title
if (plot.title != "") {
  p <- p + ggtitle(plot.title)
  # In case you want to modify the style
  #p <- p + theme(plot.title = element_text(family, face, colour, size))
}

# X-axis title

  p <- p + xlab(plot.xAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.x = element_text(family, face, colour, size))

# Y-axis title
if (plot.yAxisName != "") {
  p <- p + ylab(plot.yAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.y = element_text(family, face, colour, size))
}
if (nGroupNames != 0) {
  p <- p + scale_x_discrete(labels=groupNames)
}



ggsave(paste(c(plot.fileName, ".", format), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device=format)
