library(readr)
read_data <- function(path) {
  # Check if the file exists
  if (!file.exists(path)) {
    stop(paste0("File not found: ", path, " Stopping plot..."))
  }
  # Read data from csv file
  data <- read.table(path, sep = " ", header = TRUE, stringsAsFactors = FALSE)
  # Return the data
  data

}

# S4 for information about the plot
## BARPLOT INFO ##
setClass("Plot_info",
    slots = list(
        # Columns to use as x axis
        x = "vector",
        # Columns to use as y axis
        y = "vector",
        # Columns to use as conf_z
        conf_z = "vector",
        # Hidden bars
        hidden_bars = "vector",
        # Faceting variable
        faceting_var = "character",
        # Facet map
        facet_map = "MapSet",
        # Option to only show the mean
        show_only_mean = "logical",
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
# Use setValidity in the future
# setGeneric("check_data_info_correct",
#   function(object) {
#     standardGeneric("check_data_info_correct")
#   }
# )

# setGeneric("complete_data",
#   function(object) {
#     standardGeneric("complete_data")
#   }
# )

setMethod("initialize",
  "Plot_info",
  function(.Object, args) {
    .Object@args <- args
    .Object %<>% parse_args_plot_info()
    .Object@data <- read_data(.Object@stats_file)
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
    n_x <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 4. X axis variables
    object@x <- get_arg(object@args, n_x)
    object@args %<>% shift(n_x)
    # 5. Number of y axis variables
    n_y <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 6. Y axis variables
    object@y <- get_arg(object@args, n_y)
    object@args %<>% shift(n_y)
    # 7. Number of conf_z columns
    n_conf_z <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 8. Conf_z columns
    object@conf_z <- get_arg(object@args, n_conf_z)
    object@args %<>% shift(n_conf_z)
    # 9. Option to only show the mean
    object@show_only_mean <- as.logical(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 10. Number of hidden bars
    n_hidden_bars <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 11. Hidden bars
    if (n_hidden_bars > 0) {
      object@hidden_bars <- get_arg(object@args, n_hidden_bars)
      object@args %<>% shift(n_hidden_bars)
    }
    # 12. faceting variables
    n_faceting_vars <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    if (n_faceting_vars > 0) {
      object@facet_map <- new("MapSet", "character")
      for (i in 1 : n_faceting_vars) {
        string_arg <- get_arg(object@args, 1)
        object@args %<>% shift(1)
        string_arg %<>% str_split("=") %>% unlist()
        object@facet_map %<>% emplace_element(string_arg[1], string_arg[2])
      }
      object@faceting_var <- get_arg(object@args, 1)
      object@args %<>% shift(1)
    } 
    object
  }
)



# setMethod("complete_data",
#   signature(object = "Plot_info"),
#   function(object) {
#     n_rows <- nrow(object@data)
#     facet_levels <- unique(pull(object@data, object@faceting_var))
#     if (length(object@conf_z) > 1) {
#     # Unite the conf_z columns
#       object@data %<>% tidyr::unite("conf_z",
#         object@conf_z,
#         sep = "_",
#         remove = FALSE)
#       object@conf_z <- "conf_z"
#       print("Joining conf_z columns")
#     }
#     conf_z_levels <- unique(pull(object@data, object@conf_z))
#     object@data$conf_z %<>% factor(levels = conf_z_levels)
#     # Complete the data frame with the conf_z and x missing combinations
#     object@data %<>%
#         tidyr::complete(.data[[object@x]],
#             .data[[object@conf_z]],
#             .data[[object@faceting_var]],
#             fill = list())

#     object@data %<>% mutate_at(object@faceting_var,
#         as.character)
#     # Put faceting variables as ordered factors
#     object@data[object@faceting_var] <-
#         factor(pull(object@data, object@faceting_var), levels = facet_levels)
#     # Put conf_z and x as ordered factors
#     object@data[[object@conf_z]] %<>%
#         factor(levels = unique(object@data[[object@conf_z]]))
#     object@data[[object@x]] %<>%
#         factor(levels = unique(object@data[[object@x]]))
#     if (n_rows != nrow(object@data)) {
#       warning(paste0("The data frame was completed with missing combinations.",
#       " Filling with NA."))
#     }
#     object
#   }
# )