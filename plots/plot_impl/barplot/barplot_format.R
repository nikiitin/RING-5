library(prismatic)
source("plots/plot_impl/formats/plot_format.R")

# Define the derived class stackedBarplot_format
setClass("Barplot_format",
    contains = "plot_format",
    slots = list(
        # The number of legend names
        n_legend_names = "numeric",
        # The names that will appear in the legend
        # In the order of apparence
        legend_names = "vector",
        # The top limit of the y axis
        y_limit_top = "numeric",
        # The bottom limit of the y axis
        y_limit_bot = "numeric",
        # The number of y breaks
        n_y_breaks = "numeric",
        # The y breaks
        y_breaks = "vector",
    )
)

setMethod(
    "parse_args_format",
    signature(
        object = "Barplot_format",
        format_start_point = "numeric",
        args = "vector"
    ),
    function(object, format_start_point, args) {
        # Call parent method
        object <- callNextMethod()
        object@n_legend_names <- as.numeric(get_arg(args, 1))
        object@args %<>% shift(1)
        object@legend_names <- get_arg(args, curr_arg, object@n_legend_names)
        object@args %<>% shift(object@n_legend_names)
        object@n_y_breaks <- as.numeric(get_arg(args, 1))
        object@args %<>% shift(1)
        object@y_breaks <- as.numeric(get_arg(args, object@n_y_breaks))
        object@args %<>% shift(object@n_y_breaks)
        object@y_limit_top <- as.numeric(get_arg(args, 1))
        object@args %<>% shift(1)
        object@y_limit_bot <- as.numeric(get_arg(args, 1))
        object@args %<>% shift(1)
    }
)

# Override all needed methods from the plot_format class
# Overriding initialize method from plot_format class
setMethod(
    "initialize",
    signature(.Object = "Barplot_format"),
    function(.Object, y, args) {
        # Call parent method
        .Object <- callNextMethod()
        # Add 0.5 to x split points to center the vlines out of the bars
        .Object@format@x_split_points <- (.Object@format@x_split_points + 0.5)
        # Return the object
        .Object
    }
)

# Override check_data_format_correct method from plot_format class
setMethod(
    "check_data_format_correct",
    signature(object = "Barplot_format", df = "data.frame"),
    function(object, df) {
        # Call parent method
        callNextMethod()
        # Check there is a configuration column
        if (!("configurations" %in% colnames(df))) {
            stop("No configurations column found! Data is not correctly formatted for a barplot")
        }
        # Check if data is correct for a barplot
            # Check if number of n_legend_names is equal to number of configs
    if (object@n_legend_names > 0 &&
      object@n_legend_names != length(unique(df$configurations))) {
      warning(paste("Number of legend names is not equal to number of configs!",
        " Expected: ",
        length(unique(df$configurations)),
        " Got: ",
        object@n_legend_names, sep = ""))
    }
    }
)

setMethod(
    "apply_format",
    signature(object = "Barplot_format", plot = "ggplot", df = "data.frame"),
    function(object, plot, df) {
        # Call parent method
        plot <- callNextMethod()
        # Add the colors to the plot (one color per config)
        # using viridis color palette, which is a colorblind
        # friendly palette. In case a label is used, make it match
        # the color black/white depending on the bawckground color.
        colors <-
            farver::decode_colour(
                viridisLite::plasma(
                    length(
                        unique(
                            df$configurations
                        )
                    ),
                    direction = -1
                ),
                "rgb",
                "hcl"
            )
        label_col <- ifelse(colors[, "l"] > 50, "black", "white")
        # Assign the colors to plot and labels to legend in case
        # legend names are specified
        if (object@n_legend_names != 0) {
            plot <- plot +
                scale_fill_viridis_d(
                    option = "plasma",
                    labels = object@legend_names,
                    direction = -1
                )
        } else {
            plot <- plot +
                scale_fill_viridis_d(
                    option = "plasma",
                    direction = -1
                )
        }
        # Limit the y axis and assign labels to those
        # statistics that overgo the top limit
        if (object@y_limit_top > 0) {
            if (object@y_limit_bot > object@y_limit_top) {
                warning("Y limit bot is greater than Y limit top! skipping limits")
            } else if (object@y_limit_bot < 0) {
                warning("Y limit bot is less than 0! skipping limits")
            } else {
                # Check if any stat goes over the top limit and
                # assign a label to it
                list_of_labels <-
                    ifelse(
                        (df[, object@y] > (object@y_limit_top)),
                        format(
                            round(
                                df[, object@y],
                                2
                            ),
                            nsmall = 2
                        ),
                        NA
                    )
                # Set the breaks and the limits
                plot <- plot +
                    scale_y_continuous(
                        breaks = object@y_breaks,
                        oob = scales::squish
                    )
                plot <- plot + coord_cartesian(
                    ylim = as.numeric(
                        c(
                            object@y_limit_bot,
                            object@y_limit_top
                        )
                    )
                )
                # Add the labels to the plot
                plot <- plot +
                    geom_text(
                        position = position_dodge(.9),
                        aes(
                            label = list_of_labels,
                            group = configurations,
                            color = configurations,
                            y = object@y_limit_top
                        ),
                        show.legend = FALSE,
                        size = 2.5,
                        angle = 90,
                        hjust = "inward"
                    )
                # Set the color of the labels
                plot <- plot +
                    scale_color_manual(
                        values = label_col
                    )
            }
        }
    }
)