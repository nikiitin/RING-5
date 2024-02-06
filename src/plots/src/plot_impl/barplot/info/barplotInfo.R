require(stringr)
# Define the S4 class for a generic plot
setClass("Barplot_info",
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
        faceting_var = "character",
        # Facet map
        facet_map = "MapSet"
    )
)

setMethod("parse_args_plot_info",
  signature(object = "Barplot_info"),
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
    # 11. faceting variables
    object@n_faceting_vars <- as.numeric(get_arg(object@args, 1))
    object@args %<>% shift(1)
    if (object@n_faceting_vars > 0) {
      object@facet_map <- new("MapSet", "character")
      for (i in 1 : object@n_faceting_vars) {
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

setMethod("check_data_info_correct",
  signature(object = "Barplot_info"),
  function(object) {
    # Check that the z axis variables are in the data frame
    if (!all(object@conf_z %in% colnames(object@data))) {
      stop("The conf_z axis variables are not in the data frame.")
    }
    if (object@n_y > 1) {
      stop("Barplot only supports one y axis variable.")
    }
    if (object@n_hidden_bars >= length(unique(object@data[, object@conf_z]))) {
      stop("The number of hidden bars must be lesser than the number of conf_z columns.")
    }
    # Call parent method
    callNextMethod()
    object
  }
)

setMethod("complete_data",
  signature(object = "Barplot_info"),
  function(object) {
    n_rows <- nrow(object@data)
    # Complete the data frame with the conf_z and x missing combinations
    print(object@data)
    print(object@x)
    print(object@conf_z)
    object@data %<>% tidyr::complete(.data[[object@x]], .data[[object@conf_z]], fill = list())
    if (n_rows != nrow(object@data)) {
      warning(paste0("The data frame was completed with missing combinations.",
      " Filling with NA."))
    }
    object
  }
)