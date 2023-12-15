#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)
library(prismatic)
library(methods)
source("utils/util.R")
source("plots/plot_impl/plot.R")

# Define the S4 class for a barplot
setClass("Barplot", contains = "Plot")

# Override all needed methods from the Plot class
# Override check_data_correct method from Plot class
setMethod("check_data_correct",
  signature(object = "Barplot"),
  function(object) {
    # Call parent method
    callNextMethod(object)
    # Check if data is correct for a barplot
    # Check if there is only one stat
    if (object@n_stats != 1) {
      stop("Only one stat can be specified to barplot")
    }
  }
)

# Override create_plot method from Plot class
# need different behavior for barplot
setMethod("create_plot",
  signature(object = "Barplot"),
  function(object) {
    # We can call parent method here!
    plot <- callNextMethod(object)
    # Add the geom_bar to the plot object
    plot <- geom_bar(
      stat = "identity",
      position = "dodge",
      color = "black") +
    # Add standard deviation error bars
    plot <- geom_errorbar(
      aes(ymin = object@data_frame[, object@stat] -
        object@data_frame[, paste(object@stat, "sd", sep = ".")],
      ymax = object@data_frame[, object@stat] +
        object@data_frame[, paste(object@stat, "sd", sep = ".")]),
      width = .2,
      position = position_dodge(.9))
    # Return the plot
    plot
  }
)

# Definition complete. Now do plotting
# Take arguments from calling script
arguments <- commandArgs(trailingOnly = TRUE)

# Define variable of barplot type
# Prototype is not defined!
# This will call initialize method from Barplot class
barplot <- new("Barplot", args = arguments)
# Draw the plot as initialize method has already
# prepared all the data
draw_plot(barplot)
# Finish script