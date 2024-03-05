library(prismatic)
library(ggthemes)
source("src/plots/src/plot_impl/lineplot/styles/info/lineplotStyleInfo.R")

# Define the derived class Lineplot_default
setClass("Lineplot_default",
    contains = "Plot_style"
)

# Create_style_info with Lineplot info
setMethod(
    "create_style_info",
    signature(object = "Lineplot_default"),
    function(object) {
        # Create Lineplot style info object
        # It will define which variables will be used
        # stick to it in the rest of the styles for this kind
        # of plot
        object@style_info <- new("Lineplot_style_info",
            args = object@args
        )
        # Return the object
        object
    }
)
setMethod(
    "check_data_correct",
    signature(object = "Lineplot_default"),
    function(object) {
        # Check if data is correct for a Lineplot
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
    signature(.Object = "Lineplot_default"),
    function(.Object, plot_info, args) {
        # Call parent method
        .Object <- callNextMethod()
        # Return the object
        .Object
    }
)

setMethod(
    "apply_style",
    signature(object = "Lineplot_default", plot = "ggplot"),
    function(object, plot) {
        # Set the theme to be used
        plot <- plot + theme_hc()
        # Add specific configs to the theme
        plot <- plot + theme(
            axis.text.x = element_text(
                angle = 30,
                hjust = 1,
                size = adjust_text_size(11,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(11,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.title.y = element_text(
                size = adjust_text_size(13,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            legend.position = "top",
            legend.justification = "right",
            legend.title = element_text(
                size = adjust_text_size(13,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(11,
                    object@style_info@width,
                    object@style_info@height)
            ),
            legend.key.width = unit(
                adjust_text_size(1,
                    object@style_info@width,
                    object@style_info@height),
                "cm"),
            legend.key.height = unit(
                adjust_text_size(1,
                    object@style_info@width,
                    object@style_info@height),
                "cm"),
            strip.text = element_text(
                size = adjust_text_size(
                    8,
                    object@style_info@width,
                    object@style_info@height
                ),
                angle = 0,
                face = "bold"
            ),
            strip.placement = "outside",
            strip.background = element_rect(fill = alpha('#2eabff', 0.1), color = "white"),
            panel.spacing = unit(0.1, "cm")
        )
        # Assign the colors to plot and labels to legend in case
        # legend names are specified
        if (object@style_info@n_legend_names != 0) {
            plot <- plot +
                scale_colour_viridis_d(
                    option = "viridis",
                    labels = object@style_info@legend_names,
                    direction = 1
                )
        } else {
            plot <- plot +
                scale_colour_viridis_d(
                    option = "viridis",
                    direction = 1
                )
        }
        # # Limit the y axis and assign labels to those
        # # statistics that overgo the top limit
        if (object@style_info@y_limit_top > 0) {
            if (object@style_info@y_limit_bot > object@style_info@y_limit_top) {
                warning(paste0(
                    "Y limit bot is greater than Y limit top! ",
                    "skipping limits"
                ))
            } else if (object@style_info@y_limit_bot < 0) {
                warning("Y limit bot is less than 0! skipping limits")
            } else {
        #         # Calculate the colors that will be applied
        #         # for labels depending on its background
        #         # TODO-Note: using plasma but should be configurable
        #         colors <-
        #             farver::decode_colour(
        #                 viridisLite::viridis(
        #                     length(
        #                         unique(object@plot_info@data_frame[[object@plot_info@conf_z]])
        #                     ),
        #                     direction = 1,
        #                 ),
        #                 "rgb",
        #                 "hcl"
        #             )
        #         label_col <- ifelse(colors[, "l"] > 50, "black", "white")
                # Check if any stat goes over the top limit and
                # assign a label to it
                list_of_labels <-
                    ifelse(
                        ((object@plot_info@data_frame[, object@plot_info@y] >
                            object@style_info@y_limit_top)),
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
                        size = adjust_text_size(2,
                            object@style_info@width,
                            object@style_info@height),
                        angle = 90,
                        hjust = "inward",
                        na.rm = TRUE
                    )
        #         # Set the color of the labels
        #         plot <- plot +
        #             scale_color_manual(
        #                 values = label_col
        #             )
            }
        }
        plot <- callNextMethod()
        plot
    }
)