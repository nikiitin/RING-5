#!/usr/bin/Rscript
options(error=function()traceback(2))
source("src/utils/util.R")
source("src/plots/src/plot_impl/plot.R")
# Source it here. We do not want it to be generic :)
source("src/plots/src/plot_impl/heatmap/info/heatmapInfo.R")
library(ggh4x)
library(colourvalues)

# Define the S4 class for a Heatmap
setClass("Heatmap", contains = "Plot"
)

setMethod("create_plot_info",
  signature(object = "Heatmap"),
  function(object) {
    # Call parent method
    object@info <- new("Heatmap_info",
      args = object@args)
    object
  }
)

setMethod("add_name_columns",
  signature(object = "Heatmap"),
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
  signature(object = "Heatmap"),
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
    if (object@info@show_only_mean) {
      df <- df[df$benchmark_name == "geomean", ]
    }
    object@info@data_frame <- df
    # Return the object
    object
  }
)

# Override create_plot method from Plot class
# need different behavior for Heatmap
setMethod("create_plot",
  signature(object = "Heatmap"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Create the plot object

    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@conf_z]],
      fill = .data[[object@info@y]]
    ))
    # Add line to the plot
    # Add geometric points to convert to scatter Heatmap
    # Add error bars to the points to show the standard deviation
    object@plot <- object@plot +
      geom_tile(color = "black") +
      coord_fixed()
    list_of_labels <- format(round(object@info@data_frame[, object@info@y], 3), nsmall = 3)
    colors <- farver::decode_colour(
        colourvalues::colour_values(list_of_labels),
        "rgb",
        "hcl"
        )
    label_col <- ifelse(colors[, "l"] > 50, "black", "white")
    object@plot <- object@plot +
    geom_text(
      aes(
        label = list_of_labels),
        size = adjust_text_size(8.5,         
          object@styles@style_info@width,
          object@styles@style_info@height),
        color = label_col)
      
    # Facet by the variable specified in faceting_var
    if (object@info@n_faceting_vars > 0) {
      object@plot <- object@plot + facet_wrap(
        object@info@faceting_var)
    }
    # print(object@info@faceting_var)

    # Return the plot
    object@plot
  }
)