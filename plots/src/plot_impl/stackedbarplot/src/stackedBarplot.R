#!/usr/bin/Rscript
options(error = function() traceback(2))
source("utils/util.R")
source("plots/src/plot_impl/barplot/src/barplot.R")
# Source it here. We do not want it to be generic :)
source("plots/src/plot_impl/stackedbarplot/info/stackedBarplotInfo.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

# As most part of the code is already implemented in the Plot class
# only create_plot method needs to be overridden. Nevertheless,
# I purposedly restricted the user to always redefine create_plot_info
# method to AVOID the user to not redefine the information being used for
# different plots. This is a good practice as it will avoid the user
# to make mistakes when defining the information for a plot.

# Define the S4 class for a barplot
setClass("StackedBarplot", contains = "Barplot")



setMethod(
  "create_plot_info",
  signature(object = "StackedBarplot"),
  function(object) {
    # Call parent method
    object@info <- new("StackedBarplot_info",
      args = object@args
    )
    object
  }
)

# Override create_plot method from Plot class
# need different behavior for barplot
setMethod(
  "create_plot",
  signature(object = "StackedBarplot"),
  function(object) {
    # Build error bars data
    error_df <- object@info@data_frame %>%
      group_by(.data[[object@info@x]]) %>%
      mutate(error_bar_cumsum = cumsum(.data[[object@info@y]])) %>%
      ungroup()
    error_df %<>% mutate(
      error_bar_cumsum_ymin = error_bar_cumsum - .data[[paste(object@info@y, "sd", sep = ".")]]
    )
    error_df %<>% mutate(
      error_bar_cumsum_ymax = error_bar_cumsum + .data[[paste(object@info@y, "sd", sep = ".")]]
    )
    
    # DO NOT CALL PARENT METHOD
    # Create the plot object
    object@plot <- ggplot(error_df, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@y]]
    ))
    # Add the geom_bar to the plot object
    object@plot <- object@plot + geom_bar(
      stat = "identity",
      position = position_stack(reverse = TRUE),
      color = "black",
      aes(fill = .data[[object@info@conf_z]])
    )
    # Add standard deviation error bars

    object@plot <- object@plot + geom_errorbar(
      data = error_df,
      aes(
        ymin = .data[["error_bar_cumsum"]] -
          .data[[paste(object@info@y, "sd", sep = ".")]],
        ymax = .data[["error_bar_cumsum"]] +
          .data[[paste(object@info@y, "sd", sep = ".")]],
      ),
      width = .2
    )
    # Return the plot
    object@plot
  }
)