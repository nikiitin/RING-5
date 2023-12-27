# This file contains the style mapper function. This will allow
# to create a style object from a plot type and a style name
# dynamically at runtime depending on the kind of plot being
# used. Very practical in order to restrict the user from
# applying a style that is not compatible with the plot type.
get_style <- function(plot_type, style_name, args) {
    # Check inside plot_impl file if the plot_type exists
    # (has a folder)
    # TODO: Magic strings????? so ugly...
    plot_type_path <- paste0("plots/src/plot_impl/", plot_type)
    if (!file.exists(plot_type_path)) {
        stop(paste0("Plot type '", plot_type, "' not found!"))
    }
    # Check if the style_name exists inside the plot_type folder
    style_path <- paste0(plot_type_path, "/styles/", style_name, ".R")
    if (!file.exists(style_path)) {
        stop(paste0("Style '", style_name, "' not found for plot type '",
            plot_type, "'!"))
    }
    # Source the style file
    source(style_path)
    # Return the style object
    new(style_name, args = args)
}