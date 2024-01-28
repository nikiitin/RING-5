#!/usr/bin/Rscript
options(error=function()traceback(2))
source("src/utils/util.R")
source("src/plots/src/plot_impl/plot.R")
# Source it here. We do not want it to be generic :)
source("src/plots/src/plot_impl/barplot/info/barplotInfo.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

# As most part of the code is already implemented in the Plot class
# only create_plot method needs to be overridden. Nevertheless,
# I purposedly restricted the user to always redefine create_plot_info
# method to AVOID the user to not redefine the information being used for
# different plots. This is a good practice as it will avoid the user
# to make mistakes when defining the information for a plot.

# Define the S4 class for a barplot
setClass("Barplot", contains = "Plot"
)

setMethod("create_plot_info",
  signature(object = "Barplot"),
  function(object) {
    # Call parent method
    object@info <- new("Barplot_info",
      args = object@args)
    object
  }
)

setMethod("add_name_columns",
  signature(object = "Barplot"),
  function(object) {
    object <- callNextMethod()
    # Add conf_z columns
    object@info@data_frame %<>%
      cbind(object@info@data[object@info@conf_z])
    # Take into account that conf_z column is an already ordered factor
    # so assign back the levels to the data frame
    object@info@data_frame[, object@info@conf_z] %<>%
      factor(levels = unique(object@info@data[, object@info@conf_z]))
    # Return the object
    object
  }
)

setMethod("format_data",
  signature(object = "Barplot"),
  function(object) {
    # Call parent method
    object <- callNextMethod()
    df <- object@info@data_frame
    # Remove hidden bars from data frame, filter by conf_z
    if (object@info@n_hidden_bars > 0) {
      df <- df[!df[, object@info@conf_z] %in% object@info@hidden_bars, ]
    }
    object@info@data_frame <- df
    # Return the object
    object
  }
)


# Override create_plot method from Plot class
# need different behavior for barplot
setMethod("create_plot",
  signature(object = "Barplot"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Create the plot object
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@y]],
      fill = .data[[object@info@conf_z]]
    ))
    # Add the geom_bar to the plot object
    object@plot <- object@plot + geom_bar(
      stat = "identity",
      position = "dodge",
      color = "black")
    # Add standard deviation error bars
    object@plot <- object@plot + geom_errorbar(
      aes(ymin = object@info@data_frame[, object@info@y] -
        object@info@data_frame[, paste(object@info@y, "sd", sep = ".")],
      ymax = object@info@data_frame[, object@info@y] +
        object@info@data_frame[, paste(object@info@y, "sd", sep = ".")]),
      width = .2,
      position = position_dodge(.9))
    # Return the plot
    object@plot
  }
)