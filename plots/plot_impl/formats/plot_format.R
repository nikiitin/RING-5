library(ggthemes)
library(dplyr)
source("utils/util.R")
setClass("Plot_format",
  slots = list(
    # The title of the plot
    title = "character",
    # The name of the x axis
    x_axis_name = "character",
    # The name of the y axis
    y_axis_name = "character",
    # The width of the plot
    width = "numeric",
    # The height of the plot
    height = "numeric",
    # The format of the plot: pdf, png, etc.
    format = "character",
    # The title of the legend
    legend_title = "character",
    # The number of elements (configs) per row in the legend
    legend_n_elem_row = "numeric",
    # The number of x split points
    n_x_split_points = "numeric",
    # The x split points (dotted vertical bars splitting the plot)
    x_split_points = "vector",
    # The statistics to be used
    y = "vector"
  )
)
# Define all generic methods for the Plot_format class
setGeneric("parse_args_format",
  function(object, format_start_point, args) {
  standardGeneric("parse_args_format")
})

setGeneric("check_data_format_correct", function(object, df) {
  standardGeneric("check_data_format_correct")
})

setGeneric("apply_format", function(object, plot, df) {
  standardGeneric("apply_format")
})

# Define the parse_args method for the Plot_format class
setMethod("parse_args_format",
  signature(object = "Plot_format",
    args = "vector"),
  function(object, args) {
    # Parse the arguments and store them in the object
    # Prepare the format object
    # It will apply all format configurations to the plot
    object@title <- get_arg(args, 1)
    object@args %<>% shift(1)
    object@x_axis_name <- get_arg(args, 1)
    object@args %<>% shift(1)
    object@y_axis_name <- get_arg(args, 1)
    object@args %<>% shift(1)
    object@width <- as.numeric(get_arg(args, 1))
    object@args %<>% shift(1)
    object@height <- as.numeric(get_arg(args, 1))
    object@args %<>% shift(1)
    object@format <- get_arg(args, 1)
    object@args %<>% shift(1)
    object@legend_title <- get_arg(args, 1)
    object@args %<>% shift(1)
    object@legend_n_elem_row <- as.numeric(get_arg(args, 1))
    object@args %<>% shift(1)
    object@n_x_split_points <- as.numeric(get_arg(args, 1))
    object@args %<>% shift(1)
    object@x_split_points <- as.numeric(
      get_arg(
        args,
        object@n_x_split_points))
    object@args %<>% shift(object@n_x_split_points)
    # Return the object
    object
  }
)

# Define initialize method for the Plot class
setMethod("initialize", "Plot_format",
  function(.Object, format_start_point, y, args) {
    .Object@y <- y
    # Call the parse_args method
    #options(error=function()traceback(2))
    .Object <- parse_args_format(.Object, format_start_point, args)
    # Return the object
    .Object
  }
)

# Check data is correct
setMethod("check_data_format_correct",
  signature(object = "Plot_format", df = "data.frame"),
  function(object, df) {
    # Non-critical errors
    # Tell the user the error to fix it
    # Check if any y break is over the top limit
    if (any(object@y_breaks > object@y_limit_top)) {
      warning("Y breaks are over the top limit!")
    }
    # Check if any y break is under the bottom limit
    if (any(object@y_breaks < object@y_limit_bot)) {
      warning("Y breaks are under the bottom limit!")
    }
    # Check if x split points is below 1
    if (object@n_x_split_points < 1) {
      warning("Number of x split points is below 1!")
    }
    # Check if x split points is greater than the number of x variables
    if (object@n_x_split_points > 0 &&
     object@n_x_split_points > length(unique(df$x))) {
      warning(paste("Number of x split points is over x var number!",
        " Expected: ",
        length(unique(df$x)),
        " Got: ",
        object@n_x_split_points, sep = ""))
    }
  }
)
# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("gg", "ggplot"))
# Define the draw method for the Plot class
setMethod(
  "apply_format",
  signature(object = "Plot_format", plot = "ggplot", df = "data.frame"),
  function(object, plot, df) {
    # Apply style to the plot
    # Set x split points. An split point
    # is a dotted vertical line that splits the plot
    # into two parts (or more) to make it easier to read.
    # The split points are the x coordinates of the lines (reference
    # points are benchmarks)
    if (object@n_x_split_points > 0) {
      plot <- plot +
        geom_vline(
          xintercept = object@x_split_points,
          linetype = "dashed",
          color = "black"
        )
    }
    # Set the theme to be used
    plot <- plot + theme_hc()
    # Add specific configs to the theme
    # TODO: This should be configurable
    plot <- plot + theme(
      axis.text.x = element_text(
        angle = 30,
        hjust = 1,
        size = 10,
        face = "bold"
      ),
      axis.text.y = element_text(
        hjust = 1,
        size = 10,
        face = "bold"
      ),
      legend.position = "top",
      legend.justification = "right"
    )
    # Set the number of elements per row in the legend
    # and the title of the legend
    plot <- plot +
      guides(
        fill = guide_legend(
          nrow = object@legend_n_elem_row,
          title = object@legend_title
        )
      )
    # Set the Title
    if (object@title != "") {
      plot <- plot + ggtitle(object@title)
    }
    # Set the x axis title
    if (object@x_axis_name != "") {
      plot <- plot + xlab(object@x_axis_name)
    }
    # Set the y axis title
    if (object@y_axis_name != "") {
      plot <- plot + ylab(object@y_axis_name)
    }
    # Return the plot
    plot
  }
)