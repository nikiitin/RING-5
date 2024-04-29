#!/usr/bin/Rscript
source("src/plots/src/plot_impl/heatmap/src/heatmap.R")
# Take arguments from calling script
# TODO: make it in a more generic way
arguments <- commandArgs(trailingOnly = TRUE)
heatmap <- new("Heatmap", args = arguments)
# Draw the plot as initialize method has already
# prepared all the data
draw_plot(heatmap)
# Finish script