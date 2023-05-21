#!/usr/bin/Rscript
require(readr)
require(ggplot2)
require(ggthemes)
require(ggpubr)
require(grid)   # for the textGrob() function
require(patchwork)
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
n_lines_configs <- n_lines_configs - 1

currArg <- increment(currArg)
n_stats <- as.integer(arguments[currArg])

currArg <- increment(currArg)
if (n_stats != 1) {
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

currArg <- increment(currArg)
lines_names <- NULL
n_lines_names <- arguments[currArg]
currArg <- increment(currArg)
if (n_lines_names > 0) {
  for (i in 1:n_lines_names) {
    lines_names <- c(lines_names, arguments[currArg])
    currArg <- increment(currArg)
  }
}
format <- arguments[currArg]
# Finish arguments parsing

# Start data collection
parsed_data <- read.table(fileName, sep = " ", header=TRUE)

# Prepare Y-axis (pick stats names)
parsed_data["confLine"] <- ""
parsed_data["confLine"] <- mixStringCols(1, n_lines_configs, parsed_data)
parsed_data["x_config"] <- parsed_data[,x_config]
parsed_data["line_stat"] <- parsed_data[,line_stat]
parsed_data$confKey <- factor(parsed_data$confKey,
  levels = unique(as.character(parsed_data$confKey)),
  ordered = TRUE)
parsed_data$benchmark_name <- factor(parsed_data$benchmark_name,
  levels = unique(as.character(parsed_data$benchmark_name)),
  ordered = TRUE)
# To keep the order from the configs, turn them into a factor
if (n_lines_names > 0) {
  confs <- unique(parsed_data[,"confLine"])
  if (n_lines_names == length(confs)) {
    i <- 1
    for (conf in confs) {
      parsed_data[parsed_data["confLine"] == conf, "confLine"] <- lines_names[[i]]
      i <- increment(i)
    }
  } else {
    print("Legend names was provided but number of names was not the same than confLines")
  }

}
# Do not iterate over duplicates

vars <- unique(parsed_data[, var_iterate])
plot_list <- list()
# Iterate over selected variable
i <- 1
for (var in vars) {
  plot_data <- parsed_data[parsed_data[var_iterate] == var,]
  p <- ggplot(data=plot_data, aes(x=x_config, y=line_stat, group=confLine)) +
    geom_line(aes(linetype=confLine, color=confLine)) +
    geom_point(aes(shape=confLine))

  p <- p + scale_x_continuous(breaks=unique(plot_data[,x_config]))
  # Break x only on variables provided by user
  p <- p + theme_hc() +
    theme(axis.text.x = element_text(angle = 0, vjust = 0.5, hjust=0.5))
  p.list <- p
  # Pick breaks for y
  plot_limits <- quantile(plot_data[,line_stat], probs=c(0,1))
  value_range <- plot_limits[[2]] - plot_limits[[1]]
  medium_value_range <- plot_limits[[1]] + (value_range / 2)  
  # Why this works? well... do not ask it just works
  # Do scientific notations for quantile...
  breaks_figure <- c(as.numeric(formatC(as.numeric(as.character(plot_limits[[1]])), format="e", digits = 2)), 
      as.numeric(formatC(as.numeric(as.character(medium_value_range)), format="e", digits = 2)), 
      as.numeric(formatC(as.numeric(as.character(plot_limits[[2]])), format="e", digits = 2)))
  # Adjust the theme for list of plots
  p.list <- p.list + theme_hc() +
    theme(legend.position="none",
          axis.title.x=element_blank(),
          axis.text.x=element_text(size=5),
          axis.title.y=element_blank(),
          axis.text.y=element_text(size=5),
          plot.margin = margin(0.1,0.1,0.1,0.1, "cm")) +
    scale_y_continuous(limits=c(plot_limits[1],plot_limits[2]),
    breaks=breaks_figure)

  plot_list[[i]] <- p.list
  i <- increment(i)
  # Add parameters to the plot
  # Legend
  # For me its better to put it right-side
  # you can feel free to modify this file as you want
  # to fit your needs
  p + theme(legend.position = "right")



  ggsave(paste(c(plot.fileName, "_", var, ".png"),
    collapse = ""), width = plot.width, height = plot.height,
    units = "cm", dpi = 320, device = "png")
}
p <- ggarrange(plotlist=plot_list, nrow = 2, ncol=ceiling(length(vars) / 2) ,labels = vars,common.legend=TRUE, legend="bottom", font.label=list(size=7))

p <- annotate_figure(p, left = textGrob(line_stat, rot = 90),
                    bottom = textGrob(x_config))
    # Legend names
#  if (n_lines_names != 0) {
#    p <- p + scale_fill_discrete(name="Configs",labels = lines_names, font.label=list(size=7))
#  }
# Configure combined plot
ggsave(paste(c(plot.fileName, "_", "global", "_", ".", format),
  collapse = ""), plot = p, width = plot.width, height = plot.height,
  units = "cm", dpi = 320, device = format)