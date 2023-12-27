setClass("Barplot_style_info",
  contains = "Style_info",
  slots = list(
    # The number of x split points
    n_x_split_points = "numeric",
    # The x split points
    x_split_points = "vector",
    # The number of legend names
    n_legend_names = "numeric",
    # The names that will appear in the legend
    # In the order of apparence
    legend_names = "vector",
    # The number of y breaks
    n_y_breaks = "numeric",
    # The y breaks
    y_breaks = "vector",
    # The top limit of the y axis
    y_limit_top = "numeric",
    # The bottom limit of the y axis
    y_limit_bot = "numeric"
  )
)
setMethod(
    "parse_args_style",
    signature(
        object = "Barplot_style_info"
    ),
    function(object) {
        # Call parent method
        # 1-8. Call parent method. See plots/plot_impl/styles/styleIface.R
        object <- callNextMethod()
        # 9. Number of x split points
        object@n_x_split_points <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 10. X split points
        if (object@n_x_split_points > 0) {
            object@x_split_points <- as.numeric(
                get_arg(
                    object@args,
                    object@n_x_split_points
                )
            )
            object@args %<>% shift(object@n_x_split_points)
        }
        # 11. Number of legend names
        object@n_legend_names <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 12. Legend names
        if (object@n_legend_names > 0) {
            object@legend_names <-
                get_arg(object@args, object@n_legend_names)
            object@args %<>% shift(object@n_legend_names)
        }
        # 13. Number of y breaks
        object@n_y_breaks <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 14. Y breaks
        if (object@n_y_breaks > 0) {
            object@y_breaks <-
                as.numeric(get_arg(object@args, object@n_y_breaks))
            object@args %<>% shift(object@n_y_breaks)
        }
        # 15. Y limit top
        object@y_limit_top <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # 16. Y limit bot
        object@y_limit_bot <- as.numeric(get_arg(object@args, 1))
        object@args %<>% shift(1)
        # Return the object
        object
    }
)

setMethod(
    "check_data_style_correct",
    signature(object = "Barplot_style_info"),
    function(object) {
        # DO NOT CALL PARENT METHOD!!
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
        # Return the object
        object
    }
)