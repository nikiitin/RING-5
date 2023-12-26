#!/usr/bin/Rscript
source("utils/util.R")
source("plots/plot_impl/plot.R")
source("plots/plot_impl/barplot/barplot_format.R")

# Define the S4 class for a barplot
setClass("Barplot", contains = "Plot")

# Override all needed methods from the Plot class
# Override check_data_correct method from Plot class
setMethod("check_data_correct",
  signature(object = "Barplot"),
  function(object) {
    # Call parent method
    callNextMethod()
    # Check if data is correct for a barplot
    # Check if there is only one y stat
    if (object@n_y != 1) {
      stop("Only one stat can be specified to barplot")
    }
  }
)

# Override create_plot_format method from Plot class
setMethod("create_plot_format",
  signature(object = "Barplot"),
  function(object) {
    # Create barplot format object
    object@format <- new("Barplot_format",
      y = object@y,
      args = object@args)
    # Return the object
    object
  }
)

# Override create_plot method from Plot class
# need different behavior for barplot
setMethod("create_plot",
  signature(object = "Barplot"),
  function(object) {
    # We can call parent method here!
    # Call parent method
    plot <- callNextMethod()
    # Add the geom_bar to the plot object
    plot <- plot + geom_bar(
      stat = "identity",
      position = "dodge",
      color = "black")
    # Add standard deviation error bars
    plot <- plot + geom_errorbar(
      aes(ymin = object@data_frame[, object@y] -
        object@data_frame[, paste(object@y, "sd", sep = ".")],
      ymax = object@data_frame[, object@y] +
        object@data_frame[, paste(object@y, "sd", sep = ".")]),
      width = .2,
      position = position_dodge(.9))
    # Return the plot
    plot
  }
)

setMethod("read_and_format_data",
  signature(object = "Barplot"),
  function(object) {
    # Call parent method
    object <- callNextMethod()
    # Add 0.5 to x split points to center the vlines out of the bars
    object@format@x_split_points <- (object@format@x_split_points + 0.5)
    # Return the object
    object
  }
)
# Definition complete. Now do plotting
# Take arguments from calling script
# TODO: make it in a more generic way
arguments <- commandArgs(trailingOnly = TRUE)
# Define variable of barplot type
# Prototype is not defined!
# This will call initialize method from Barplot class
barplot <- new("Barplot", args = arguments)
# Draw the plot as initialize method has already
# prepared all the data
draw_plot(barplot)
# Finish script