# S4 for styles applied to the plot
setClass("Plot_style",
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
    # Args to parse
    args = "vector",
    # The names that will appear in the legend
    # In the order of apparence
    legend_names = "vector",
    # Y breaks
    y_breaks = "vector",
    # The top limit of the y axis
    y_limit_top = "numeric",
    # The bottom limit of the y axis
    y_limit_bot = "numeric"
  )
)
setGeneric("parse_args_style",
  function(object) {
  standardGeneric("parse_args_style")
})

# TODO: Use setValidity in the future

setMethod("initialize",
  "Plot_style",
  function(.Object, args) {
    .Object@args <- args
    .Object %<>% parse_args_style()
    .Object
  }
)

# Define the parse_args method for the Plot_style class
setMethod("parse_args_style",
  signature(object = "Plot_style"),
  function(object) {
    # Parse the arguments and store them in the object
    # Prepare the format object
    # It will apply all format configurations to the plot
    # 1. Title
    object@title <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 2. X axis name
    object@x_axis_name <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 3. Y axis name
    object@y_axis_name <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 4. Width (in cm?) of the plot file
    object@width <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 5. Height (in cm?) of the plot file
    object@height <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 6. Format of the plot file (pdf, png, etc.)
    object@format <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 7. Legend title
    object@legend_title <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 8. Number of elements per row in the legend
    object@legend_n_elem_row <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 11. Number of legend names
    n_legend_names <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 12. Legend names
    if (n_legend_names > 0) {
      object@legend_names <-
        get_arg(object@args, n_legend_names)
      object@args %<>% shift(n_legend_names)
    }
    # 13. Number of y breaks
    n_y_breaks <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 14. Y breaks
    if (n_y_breaks > 0) {
      object@y_breaks <-
        as.numeric(get_arg(object@args, n_y_breaks))
      object@args %<>% shift(n_y_breaks)
    }
    # 15. Y limit top
    object@y_limit_top <- suppressWarnings(
      as.numeric(get_arg(object@args, 1)))
    object@args %<>% shift(1)
    # 16. Y limit bot
    object@y_limit_bot <- suppressWarnings(
      as.numeric(get_arg(object@args, 1)))
    object@args %<>% shift(1)
    # Return the object
    object
  }
)