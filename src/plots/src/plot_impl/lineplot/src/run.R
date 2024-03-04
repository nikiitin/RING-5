#!/usr/bin/Rscript
source("src/plots/src/plot_impl/lineplot/src/lineplot.R")
# Take arguments from calling script
# TODO: make it in a more generic way
arguments <- commandArgs(trailingOnly = TRUE)
lineplot <- new("Lineplot", args = arguments)
# Draw the plot as initialize method has already
# prepared all the data
draw_plot(lineplot)
# Finish script