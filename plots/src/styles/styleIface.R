source("plots/src/styles/info/styleInfo.R")
setClass("Plot_style",
  slots = list(
    # The plot info
    plot_info = "Plot_info",
    # Style info for this plot
    style_info = "Style_info",
    args = "vector"
  )
)
# Define all generic methods for the Plot_style class
setGeneric("apply_style", function(object, plot) {
  standardGeneric("apply_style")
})

setGeneric("create_style_info", function(object) {
  standardGeneric("create_style_info")
})

setGeneric("check_data_correct", function(object) {
  standardGeneric("check_data_correct")
})

setGeneric("set_plot_info", function(object, plot_info) {
  standardGeneric("set_plot_info")
})

setMethod("set_plot_info",
  signature(object = "Plot_style", plot_info = "Plot_info"),
  function(object, plot_info) {
    object@plot_info <- plot_info
    object
  }
)

# Define initialize method for the Plot class
setMethod("initialize", "Plot_style",
  function(.Object, args) {
    # Call the parse_args method
    #options(error=function()traceback(2))
    .Object@args <- args
    .Object %<>% create_style_info()
    # keep args updated
    .Object@args <- .Object@style_info@args
    # Return the object
    .Object
  }
)

setMethod("check_data_correct",
  signature(object = "Plot_style"),
  function(object) {
    warning("check_data_correct not implemented for this style!")
  }
)

setMethod("create_style_info", "Plot_style",
  function(object) {
    # Create style info object
    object@style_info <- new("Style_info",
      args = object@args)
    # Return the object
    object
  }
)

# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("gg", "ggplot"))
# Define the draw method for the Plot class
setMethod(
  "apply_style",
  signature(object = "Plot_style", plot = "ggplot"),
  function(object, plot) {
    check_data_correct(object)
    # Apply style to the plot
    # Set the number of elements per row in the legend
    # and the title of the legend
    plot <- plot +
      guides(
        fill = guide_legend(
          nrow = object@style_info@legend_n_elem_row,
          title = object@style_info@legend_title
        )
      )
    # Set the Title
    if (object@style_info@title != "") {
      plot <- plot + ggtitle(object@style_info@title)
    }
    # Set the x axis title
    if (object@style_info@x_axis_name != "") {
      plot <- plot + xlab(object@style_info@x_axis_name)
    }
    # Set the y axis title
    if (object@style_info@y_axis_name != "") {
      plot <- plot + ylab(object@style_info@y_axis_name)
    }
    # Return the plot
    plot
  }
)