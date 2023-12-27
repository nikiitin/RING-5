library(readr)
read_data <- function(path) {
  # Check if the file exists
  if (!file.exists(path)) {
    stop(paste0("File not found: ", path, " Stopping plot..."))
  }
  # Read data from csv file
  data <- read.table(path, sep = " ", header = TRUE, stringsAsFactors = TRUE)
  # Return the data
  data

}

# Define the S4 class for a generic plot
setClass("Plot_info",
  # Define the fields of the class
  slots = list(
    # Number of x axis variables
    n_x = "numeric",
    # Columns to use as x axis
    x = "vector",
    # Number of y axis variables
    n_y = "numeric",
    # Columns to use as y axis
    y = "vector",
    # The path to the file where the plot will be saved
    result_path = "character",
    # The path to the file containing the data to be plotted
    stats_file = "character",
    # The number of legend names
    data = "data.frame",
    # Data frame to be plotted
    data_frame = "data.frame",
    # Args to parse
    args = "vector"
  )
)

# Define all generic methods for the Plot info class
setGeneric("parse_args_plot_info",
  function(object) {
    standardGeneric("parse_args_plot_info")
  }
)
setGeneric("check_data_info_correct",
  function(object) {
    standardGeneric("check_data_info_correct")
  }
)

setMethod("initialize",
  "Plot_info",
  function(.Object, args) {
    .Object@args <- args
    .Object %<>% parse_args_plot_info()
    .Object@data <- read_data(.Object@stats_file)
    .Object %<>% check_data_info_correct()
    .Object
  }
)
setMethod("parse_args_plot_info",
  signature(object = "Plot_info"),
  function(object) {
    # 1. Path to the file containing the data to be plotted
    object@stats_file <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 2. Path to the file where the plot will be saved
    object@result_path <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # 3. Number of x axis variables
    object@n_x <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 4. X axis variables
    object@x <- get_arg(object@args, object@n_x)
    object@args %<>% shift(object@n_x)
    # 5. Number of y axis variables
    object@n_y <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 6. Y axis variables
    object@y <- get_arg(object@args, object@n_y)
    object@args %<>% shift(object@n_y)
    object
  }
)

setMethod("check_data_info_correct",
  signature(object = "Plot_info"),
  function(object) {
    # Check that the data is correct
    # Check that the data frame is not empty
    if (nrow(object@data) == 0) {
      stop("The data frame is empty.")
    }
    # Check that the number of x axis variables is greater than 0
    if (object@n_x <= 0) {
      stop("The number of x axis variables is less than 1.")
    }
    # Check that the number of y axis variables is greater than 0
    if (object@n_y <= 0) {
      stop("The number of y axis variables is less than 1.")
    }
    # Check that the x axis variables are in the data frame
    if (!all(object@x %in% colnames(object@data))) {
      stop("The x axis variables are not in the data frame.")
    }
    # Check that the y axis variables are in the data frame
    if (!all(object@y %in% colnames(object@data))) {
      stop("The y axis variables are not in the data frame.")
    }
    object
  }
)