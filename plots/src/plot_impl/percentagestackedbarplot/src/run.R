#!/usr/bin/Rscript
source("plots/src/plot_impl/percentagestackedbarplot/src/percentageStackedBarplot.R")
# Take arguments from calling script
# TODO: make it in a more generic way
arguments <- commandArgs(trailingOnly = TRUE)
# Define variable of stackedBarplot type
# Prototype is not defined!
# This will call initialize method from StackedBarplot class
barplot <- new("PercentageStackedBarplot", args = arguments)
# Draw the plot as initialize method has already
# prepared all the data
draw_plot(barplot)
# Finish script