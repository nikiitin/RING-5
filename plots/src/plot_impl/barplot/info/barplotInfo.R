# Define the S4 class for a generic plot
setClass("Barplot_info",
    contains = "Plot_info",
    slots = list(
        # Number of conf_z columns
        n_conf_z = "numeric",
        # Columns to use as conf_z
        conf_z = "vector"
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
    object
  }
)

setMethod("check_data_info_correct",
  signature(object = "Barplot_info"),
  function(object) {
    # Call parent method
    callNextMethod()
    # Check that the z axis variables are in the data frame
    if (!all(object@conf_z %in% colnames(object@data))) {
      stop("The conf_z axis variables are not in the data frame.")
    }
    if (object@n_y > 1) {
      stop("Barplot only supports one y axis variable.")
    }
    object
  }
)