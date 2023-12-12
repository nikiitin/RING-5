#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)
library(prismatic)
source("utils/util.R")
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
currArg <- increment(currArg)
legend_title <- arguments[currArg]
currArg <- increment(currArg)
legend.n_elem_row <- arguments[currArg]
print(legend.n_elem_row)
currArg <- increment(currArg)

plot.xSplitPoints <- NULL
plot.nXSplitPoints <- arguments[currArg]
currArg <- increment(currArg)
if (plot.nXSplitPoints > 0) {
  for (i in 1:plot.nXSplitPoints) {
    plot.xSplitPoints <- c(plot.xSplitPoints, arguments[currArg])
    currArg <- increment(currArg)
  }
  plot.xSplitPoints <- as.numeric(plot.xSplitPoints)
  plot.xSplitPoints <- plot.xSplitPoints + 0.5
}
# Finish arguments parsing

# Start data collection
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)

stat.sd <- paste(stat, "sd", sep=".")
# To keep the order from the configs and benchmarks, turn them into a factor

parsed_data$conf_names <- factor(parsed_data$conf_names,
  levels = unique(as.character(parsed_data$conf_names)),
  ordered = TRUE)
parsed_data$benchmark_name <- factor(parsed_data$benchmark_name,
  levels = unique(as.character(parsed_data$benchmark_name)),
  ordered = TRUE)

# Basic plot
# Just plot the bar and sd
p <- ggplot(parsed_data, aes(x=benchmark_name, fill=conf_names, y=parsed_data[,stat])) +
  geom_bar(stat="identity", position="dodge", color="black") +
  geom_errorbar(aes(ymin=parsed_data[,stat] - parsed_data[,stat.sd], ymax=parsed_data[,stat] + parsed_data[,stat.sd]), width=.2, position=position_dodge(.9))
if (plot.nXSplitPoints > 0) {
  p <- p + geom_vline(xintercept = plot.xSplitPoints, linetype="dashed", color = "black")
}
# Here you can change the theme  
p <- p + theme_hc()
p <- p + theme(axis.text.x = element_text(angle = 30, hjust=1, size=10, face="bold"),
	      axis.text.y = element_text(hjust=1, size=10, face="bold"),
        legend.position="top", legend.justification="right")
#p <- p + scale_x_discrete(guide = guide_axis(n.dodge = 2))
# Add parameters to the plot
# Legend names
colors_to_print <- farver::decode_colour(viridisLite::magma(length(unique(parsed_data$conf_names)), direction = -1), "rgb", "hcl")
label_col <- ifelse(colors_to_print[, "l"] > 50, "black", "white")

if (nLegendNames != 0) {
  p <- p + scale_fill_viridis_d(option="plasma", labels=legendNames, direction = -1)
} else {
  p <- p + scale_fill_viridis_d(option="plasma", direction = -1)
}
#Number of elements per row in legend


p <- p + guides(fill=guide_legend(nrow=as.numeric(legend.n_elem_row),title=legend_title))

# Breaks
y_breaks <- as.numeric(y_breaks)

print(label_col)
# Limits
if (y_limit_top > y_limit_bot) {
    limits <- c(y_limit_bot, y_limit_top)
    hard_limits <- c(y_limit_bot, y_limit_top - (y_limit_top * 0.05))
    list_of_labels <- ifelse((parsed_data[,stat] > (y_limit_top)), format(round(parsed_data[,stat], 2), nsmall = 2), NA)
    p <- p + scale_y_continuous(breaks = y_breaks, oob=scales::squish)
    p <- p + coord_cartesian(ylim=as.numeric(limits))
    p <- p + geom_text(position = position_dodge(.9), 
      aes(label = list_of_labels, group=conf_names, color = conf_names, y=y_limit_top),
      show.legend = FALSE, size=2.5, angle=90, hjust = "inward")
    p <- p + scale_color_manual(values = label_col)
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

ggsave(paste(c(plot.statsFile, ".", format), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device=format)
