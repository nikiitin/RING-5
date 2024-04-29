# FIXME
setClass("Heatmap_style_info",
  contains = "Style_info",
  slots = list(    
    # The number of x names
    n_x_names = "numeric",
    # The x names
    x_names = "vector",
    # The number of y names
    n_y_names = "numeric",
    # The y names
    y_names = "vector"
  )
)
setMethod(
    "parse_args_style",
    signature(
        object = "Heatmap_style_info"
    ),
    function(object) {
        # Call parent method
        # 1-8. Call parent method. See plots/plot_impl/styles/styleIface.R
        object <- callNextMethod()

        # 9. Number of x names
        object@n_x_names <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 10. x names
        if (object@n_x_names > 0) {
            object@x_names <-
                get_arg(object@args, object@n_x_names)
            object@args %<>% shift(object@n_x_names)
        }
        # 11. Number of y names
        object@n_y_names <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 12. y names
        if (object@n_y_names > 0) {
            object@y_names <-
                get_arg(object@args, object@n_y_names)
            object@args %<>% shift(object@n_y_names)
        }
        # Return the object
        object
    }
)

setMethod(
    "check_data_style_correct",
    signature(object = "Heatmap_style_info"),
    function(object) {
        # Return the object
        object
    }
)