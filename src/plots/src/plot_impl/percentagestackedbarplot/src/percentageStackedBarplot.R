#!/usr/bin/Rscript
options(error = function() traceback(2))
require(tidyr)
source("src/utils/util.R")
source("src/plots/src/plot_impl/stackedbarplot/src/stackedBarplot.R")
# Source it here. We do not want it to be generic :)
source("src/plots/src/plot_impl/percentagestackedbarplot/info/percentageStackedBarplotInfo.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

# As most part of the code is already implemented in the Plot class
# only create_plot method needs to be overridden. Nevertheless,
# I purposedly restricted the user to always redefine create_plot_info
# method to AVOID the user to not redefine the information being used for
# different plots. This is a good practice as it will avoid the user
# to make mistakes when defining the information for a plot.

# Define the S4 class for a barplot
setClass("PercentageStackedBarplot", contains = "StackedBarplot")



setMethod(
  "create_plot_info",
  signature(object = "PercentageStackedBarplot"),
  function(object) {
    # Call parent method
    object@info <- new("PercentageStackedBarplot_info",
      args = object@args
    )
    object
  }
)


# Override create_plot method from Plot class
# need different behavior for barplot
setMethod(
  "create_plot",
  signature(object = "PercentageStackedBarplot"),
  function(object) {
    # Create the plot object, use normalized results as y axis
    object@info@data_frame %<>% pivot_longer(
      cols = object@info@y,
      names_to = NULL,
      values_to = "value"
    )
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = value,
      fill = object@info@y
    ))
    # Add the geom_bar to the plot object. Use position_fill to
    # stack the bars and reverse = TRUE to have the bars in the
    # same order as the legend. Fill will automatically turn
    # everything into percentages
    object@plot <- object@plot + geom_bar(
      stat = "identity",
      position = position_fill(reverse = TRUE),
      color = "black"
    )

    # # Add standard deviation error bars, use the caculated
    # # error_bar as y axis
    # object@plot <- object@plot + geom_errorbar(
    #   data = object@info@data_frame,
    #   aes(
    #     ymin = .data[["error_bar_start"]] - errors,
    #     ymax = .data[["error_bar_start"]] + errors,
    #   ),
    #   width = .2
    # )
    # Return the plot
    object@plot
  }
)