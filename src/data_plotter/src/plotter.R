#!/usr/bin/Rscript
source("src/data_plotter/src/plot_iface/plot.R")

# Take the arguments from the command line
args <- commandArgs(trailingOnly = TRUE)

# Pick the first argument as the plot type
plot_type <- args[1]
# Shift the arguments
args %<>% shift(1)

# Source the plot type
source(paste0("src/data_plotter/src/plots/", plot_type, ".R"))

# Create the plot object
plot <- new(plot_type, args)

# Draw the plot
draw_plot(plot)