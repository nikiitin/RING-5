setClass("Style_info",
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
    args = "vector"
  )
)

setGeneric("parse_args_style",
  function(object) {
  standardGeneric("parse_args_style")
})

setGeneric("check_data_style_correct",
  function(object) {
  standardGeneric("check_data_style_correct")
})

setMethod("initialize",
  "Style_info",
  function(.Object, args) {
    .Object@args <- args
    .Object %<>% parse_args_style()
    .Object %<>% check_data_style_correct()
    .Object
  }
)


# Define the parse_args method for the Plot_style class
setMethod("parse_args_style",
  signature(object = "Style_info"),
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
    # Return the object
    object
  }
)

# Check data is correct
setMethod("check_data_style_correct",
  signature(object = "Style_info"),
  function(object) {
    warning("check_data_style_correct method must be implemented!")
  }
)