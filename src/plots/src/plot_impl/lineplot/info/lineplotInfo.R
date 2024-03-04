require(stringr)
require(tidyr)
# Define the S4 class for a generic plot
setClass("Lineplot_info",
    contains = "Plot_info",
    slots = list(
        # Number of conf_z columns
        n_conf_z = "numeric",
        # Columns to use as conf_z
        conf_z = "vector",
        # Number of hidden bars
        n_hidden_bars = "numeric",
        # Hidden bars
        hidden_bars = "vector",
        # Number of faceting variables
        n_faceting_vars = "numeric",
        # Faceting variable
        faceting_var = "character"
    )
)

setMethod("parse_args_plot_info",
  signature(object = "Lineplot_info"),
  function(object) {
    # 1-6. Call parent method. See plots/plot_impl/info/plotInfo.R
    object <- callNextMethod()
    # 7. Number of conf_z columns
    object@n_conf_z <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 8. Conf_z columns
    object@conf_z <- get_arg(object@args, object@n_conf_z)
    object@args %<>% shift(object@n_conf_z)
     # 9. Number of hidden bars
    object@n_hidden_bars <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    # 10. Hidden bars
    if (object@n_hidden_bars > 0) {
      object@hidden_bars <- get_arg(object@args, object@n_hidden_bars)
      object@args %<>% shift(object@n_hidden_bars)
    }
    # 11. Number of faceting variables
    object@n_faceting_vars <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    if (object@n_faceting_vars > 1) {
      stop("Lineplot only allows one faceting variable.")
    }
    # 12. Faceting variable
    if (object@n_faceting_vars > 0) {
      object@faceting_var <- get_arg(object@args, object@n_faceting_vars)
      object@args %<>% shift(object@n_faceting_vars)
    }
    object
  }
)

setMethod("check_data_info_correct",
  signature(object = "Lineplot_info"),
  function(object) {
    # Check that the z axis variables are in the data frame
    if (!all(object@conf_z %in% colnames(object@data))) {
      stop("The conf_z axis variables are not in the data frame.")
    }
    if (object@n_y > 1) {
      stop("Lineplot only supports one y axis variable.")
    }
    if (object@n_hidden_bars >= length(unique(object@data[, object@conf_z]))) {
      stop("The number of hidden bars must be lesser than the number of conf_z columns.")
    }
    # Call parent method
    object <- callNextMethod()
    object
  }
)

setMethod("complete_data",
  signature(object = "Lineplot_info"),
  function(object) {
    if (object@n_conf_z > 1) {
      object@data %<>% tidyr::unite("conf_z",
        object@conf_z,
        sep = "_",
        remove = FALSE)
      object@data$conf_z %<>% factor(levels = unique(object@data$conf_z)) 
      object@conf_z <- "conf_z"
    }
    n_rows <- nrow(object@data)
    # Complete the data frame with the conf_z and x missing combinations
    object@data %<>% tidyr::complete(.data[[object@x]], .data[[object@conf_z]], .data[[object@faceting_var]], fill = list())
    if (n_rows != nrow(object@data)) {
      warning(paste0("The data frame was completed with missing combinations.",
      " Filling with NA."))
    }
    object
  }
)