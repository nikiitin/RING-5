source("src/data_plotter/src/plots/groupedStackedBarplot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("groupedStackedBarplotacc", contains = "groupedStackedBarplot")

setMethod(
    "apply_style",
    signature(object = "groupedStackedBarplotacc"),
    function(object) {
        # Apply style to the plot
        # Set the number of elements per row in the legend
        # and the title of the legend
        object@plot <- object@plot +
            guides(
                fill = guide_legend(
                    nrow = object@styles@legend_n_elem_row,
                    title = object@styles@legend_title,
                    title.position = "left"
                )
            )

        # Set the Title
        if (object@styles@title != "") {
            object@plot <- object@plot + ggtitle(object@styles@title)
        }
        # Set the x axis title
        if (object@styles@x_axis_name != "") {
            object@plot <- object@plot + xlab(object@styles@x_axis_name)
        }
        # Set the y axis title
        if (object@styles@y_axis_name != "") {
            object@plot <- object@plot + ylab(object@styles@y_axis_name)
        }
        # Label x axis with the legend names if specified
        # Label names were conf_z names on other plots
        if (length(object@styles@legend_names) > 0) {
            object@plot <- object@plot + scale_x_discrete(
                labels = object@styles@legend_names
            )
        }

        # Set the theme to be used
        object@plot <- object@plot + theme_hc()
        # Add specific configs to the theme
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                angle = 45,
                hjust = 1,
                size = adjust_text_size(
                    18,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(
                    18,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            axis.title.x = element_blank(),
            axis.title.y = element_text(
                size = adjust_text_size(
                    18,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            legend.position = c(0.5,0.9),
            # legend.position = "top",
            # legend.justification = "right",
            legend.background = element_blank(),
            legend.box.background = element_rect(fill = "white", color = "black"),
            legend.title = element_text(
                size = adjust_text_size(
                    19,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(
                    19,
                    object@styles@width,
                    object@styles@height
                )
            ),
            legend.key.width = unit(
                adjust_text_size(
                    1,
                    object@styles@width,
                    object@styles@height
                ),
                "cm"
            ),
            legend.key.height = unit(
                adjust_text_size(
                    1,
                    object@styles@width,
                    object@styles@height
                ),
                "cm"
            ),
            legend.box.margin = margin(-3, 0, -3, 0),
            plot.margin = margin(5, 5, 5, 5),
            strip.text = element_text(
                size = adjust_text_size(
                    19,
                    object@styles@width,
                    object@styles@height
                ),
                angle = 0,
                face = "bold"
            ),
            strip.placement = "outside",
            strip.background =
                element_rect(fill = alpha("#2eabff", 0.1), color = "white"),
            panel.spacing = unit(0.1, "cm"),
        ) # Added facet specific configs

        # Assign the colors to plot
        # Get stacked color vector
        # color_index_vector <- get_stack_discrete_color_vector(
        #     length(unique(object@info@data_frame$entries))
        #     )
        # # Get the colors from the viridis palette
        # color_vector <- viridis::viridis(length(color_index_vector))
        color_vector <- viridis::viridis(
            length(unique(object@info@data_frame$entries))
        )
        # Apply the specific order from the color index vector
        # color_vector <- color_vector[color_index_vector * (length(color_vector) - 1) + 1]
        object@plot <- object@plot +
            scale_fill_manual(
                values = color_vector
            )

        # Set the breaks
        if (length(object@styles@y_breaks) > 0) {
            object@plot <- object@plot +
                scale_y_continuous(
                    breaks = object@styles@y_breaks,
                    limits = c(
                        min(object@styles@y_breaks),
                        max(object@styles@y_breaks)
                    ),
                    oob = scales::squish,
                    expand = c(0, 0)
                )
        }
        object
    }
)