library(prismatic)
library(ggthemes)
source("plots/src/plot_impl/barplot/styles/info/barplotStyleInfo.R")

# Define the derived class Barplot_default
setClass("Barplot_default",
    contains = "Plot_style"
)

# Create_style_info with Barplot info
setMethod(
    "create_style_info",
    signature(object = "Barplot_default"),
    function(object) {
        # Create barplot style info object
        # It will define which variables will be used
        # stick to it in the rest of the styles for this kind
        # of plot
        object@style_info <- new("Barplot_style_info",
            args = object@args
        )
        # Return the object
        object
    }
)
setMethod(
    "check_data_correct",
    signature(object = "Barplot_default"),
    function(object) {
        # Check if x split points is greater than the number of x variables
        if (object@style_info@n_x_split_points > 0 &&
            object@style_info@n_x_split_points > length(
                unique(
                    object@plot_info@data[
                        object@plot_info@x
                    ]
                )
            )) {
            warning(paste("Number of x split points is over x var number!",
                " x vars: ",
                length(
                    unique(
                        object@plot_info@data[
                            object@plot_info@x
                        ]
                    )
                ),
                " Got: ",
                object@style_info@n_x_split_points,
                sep = ""
            ))
        }
        # Check if data is correct for a barplot
        # Check if number of n_legend_names is equal to number of configs
        if (object@style_info@n_legend_names > 0 &&
            object@style_info@n_legend_names != nrow(
                unique(
                    object@plot_info@data[
                        object@plot_info@conf_z
                    ]
                )
            )
        ) {
            warning(paste0(
                "Number of legend names is ",
                "not equal to number of configs!",
                " Expected: ",
                nrow(unique(object@plot_info@data[
                    object@plot_info@conf_z
                ])),
                " Got: ",
                object@style_info@n_legend_names
            ))
        }
    }
)


# Override all needed methods from the plot_format class
# Overriding initialize method from plot_format class
setMethod(
    "initialize",
    signature(.Object = "Barplot_default"),
    function(.Object, plot_info, args) {
        # Call parent method
        .Object <- callNextMethod()
        # Add 0.5 to x split points to center the vlines out of the bars
        .Object@style_info@x_split_points <-
            (.Object@style_info@x_split_points + 0.5)
        # Return the object
        .Object
    }
)

setMethod(
    "apply_style",
    signature(object = "Barplot_default", plot = "ggplot"),
    function(object, plot) {
        # x split points
        if (object@style_info@n_x_split_points > 0) {
            plot <- plot +
                geom_vline(
                    xintercept = object@style_info@x_split_points,
                    linetype = "dashed",
                    color = "black"
                )
        }
        # Set the theme to be used
        plot <- plot + theme_hc()
        # Add specific configs to the theme
        plot <- plot + theme(
            axis.text.x = element_text(
                angle = 30,
                hjust = 1,
                size = 10,
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = 10,
                face = "bold"
            ),
            legend.position = "top",
            legend.justification = "right"
        )
        # Assign the colors to plot and labels to legend in case
        # legend names are specified
        if (object@style_info@n_legend_names != 0) {
            plot <- plot +
                scale_fill_viridis_d(
                    option = "plasma",
                    labels = object@style_info@legend_names,
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
        if (object@style_info@y_limit_top > 0) {
            if (object@style_info@y_limit_bot > object@style_info@y_limit_top) {
                warning(paste0(
                    "Y limit bot is greater than Y limit top! ",
                    "skipping limits"
                ))
            } else if (object@style_info@y_limit_bot < 0) {
                warning("Y limit bot is less than 0! skipping limits")
            } else {
                # Calculate the colors that will be applied
                # for labels depending on its background
                # TODO-Note: using plasma but should be configurable
                colors <-
                    farver::decode_colour(
                        viridisLite::plasma(
                            length(
                                object@plot_info@data_frame[[object@plot_info@conf_z]]
                            ),
                            direction = -1,
                        ),
                        "rgb",
                        "hcl"
                    )
                label_col <- ifelse(colors[, "l"] > 50, "black", "white")
                # Check if any stat goes over the top limit and
                # assign a label to it
                list_of_labels <-
                    ifelse(
                        (object@plot_info@data_frame[, object@plot_info@y] >
                            (object@style_info@y_limit_top)),
                        format(
                            round(
                                object@plot_info@data_frame[
                                    ,
                                    object@plot_info@y
                                ],
                                2
                            ),
                            nsmall = 2
                        ),
                        NA
                    )
                # Set the breaks and the limits
                plot <- plot +
                    scale_y_continuous(
                        breaks = object@style_info@y_breaks,
                        oob = scales::squish
                    )
                plot <- plot + coord_cartesian(
                    ylim = as.numeric(
                        c(
                            object@style_info@y_limit_bot,
                            object@style_info@y_limit_top
                        )
                    )
                )
                # Add the labels to the plot
                plot <- plot +
                    geom_text(
                        position = position_dodge(.9),
                        aes(
                            label = list_of_labels,
                            group = .data[[object@plot_info@conf_z]],
                            color = .data[[object@plot_info@conf_z]],
                            y = object@style_info@y_limit_top
                        ),
                        show.legend = FALSE,
                        size = 3,
                        angle = 90,
                        hjust = "inward",
                        na.rm = TRUE
                    )
                # Set the color of the labels
                plot <- plot +
                    scale_color_manual(
                        values = label_col
                    )
            }
        }
        plot <- callNextMethod()
        plot
    }
)