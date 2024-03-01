#!/usr/bin/Rscript
options(error=function()traceback(2))
source("src/utils/util.R")
source("src/plots/src/plot_impl/plot.R")
# Source it here. We do not want it to be generic :)
source("src/plots/src/plot_impl/lineplot/info/lineplotInfo.R")
library(ggh4x)

# Define the S4 class for a lineplot
setClass("Lineplot", contains = "Plot"
)

setMethod("create_plot_info",
  signature(object = "Lineplot"),
  function(object) {
    # Call parent method
    object@info <- new("Lineplot_info",
      args = object@args)
    object
  }
)

setMethod("add_name_columns",
  signature(object = "Lineplot"),
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
  signature(object = "Lineplot"),
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
# need different behavior for Lineplot
setMethod("create_plot",
  signature(object = "Lineplot"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Create the plot object
    object@plot <- ggplot(object@info@data_frame, aes(
      x = "",
      y = .data[[object@info@y]],
      fill = .data[[object@info@conf_z]]
    ))
    # Add the geom_bar to the plot object
    object@plot <- object@plot + geom_bar(
      stat = "identity",
      position = "dodge",
      color = "black")

    # Add the facet grid to the plot object. Switch it in to X,
    # this enforce style to group variables in x axis
    
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