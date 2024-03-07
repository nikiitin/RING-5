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
      bind_cols(object@info@data[object@info@conf_z])
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
    if (object@info@n_faceting_vars > 0) {
      df %<>% bind_cols(object@info@data[object@info@faceting_var])
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
    print(object@info@data_frame)
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@y]],
      group = .data[[object@info@conf_z]]
    ))
    # Add line to the plot
    # Add geometric points to convert to scatter lineplot
    # Add error bars to the points to show the standard deviation
    object@plot <- object@plot +
      geom_line(
        aes(linetype = .data[[object@info@conf_z]],
          color = .data[[object@info@conf_z]]),
        alpha = 0.6,
        linewidth = adjust_text_size(0.8,
                    object@styles@style_info@width,
                    object@styles@style_info@height)) +
      geom_point(
         aes(shape = .data[[object@info@conf_z]], color = .data[[object@info@conf_z]]),
         size = adjust_text_size(1.8,
                    object@styles@style_info@width,
                    object@styles@style_info@height)) +
      geom_errorbar(
        aes(ymin = object@info@data_frame[, object@info@y] -
          object@info@data_frame[, paste(object@info@y, "sd", sep = ".")],
        ymax = object@info@data_frame[, object@info@y] +
          object@info@data_frame[, paste(object@info@y, "sd", sep = ".")],
        color = .data[[object@info@conf_z]]),
        width = .3)

    # Facet by the variable specified in faceting_var
    if (object@info@n_faceting_vars > 0) {
      object@plot <- object@plot + facet_wrap(
        ~ .data[[object@info@faceting_var]], scales = "free")
    }

    # Return the plot
    object@plot
  }
)