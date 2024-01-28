source("src/plots/src/plot_impl/barplot/styles/Barplot_default.R")
source("src/plots/src/plot_impl/stackedbarplot/styles/info/stackedBarplotStyleInfo.R")

# Define the derived class Barplot_default
setClass("StackedBarplot_default",
    contains = "Barplot_default"
)

# Create_style_info with Barplot info
setMethod(
    "create_style_info",
    signature(object = "StackedBarplot_default"),
    function(object) {
        # Create barplot style info object
        # It will define which variables will be used
        # stick to it in the rest of the styles for this kind
        # of plot
        object@style_info <- new("StackedBarplot_style_info",
            args = object@args
        )
        # Return the object
        object
    }
)

setMethod("check_data_correct",
    signature(object = "StackedBarplot_default"),
    function(object) {
        # Call parent method
        callNextMethod()
        # Do not apply limits to the y axis,
        # in any case, the user should use the breaks
        if (!is.na(object@style_info@y_limit_top) ||
            !is.na(object@style_info@y_limit_bot)) {
            warning(paste0("Stacked barplots are not intended to",
                " have limits on the y axis. If you want to set any limits",
                " use the breaks instead. (on your own risk)",
                " Ignoring the limits."))
        }
    }
)

setMethod(
    "apply_style",
    signature(object = "StackedBarplot_default", plot = "ggplot"),
    function(object, plot) {
        check_data_correct(object)
        # Apply style to the plot
        # Set the number of elements per row in the legend
        # and the title of the legend
        plot <- plot +
            guides(
                fill = guide_legend(
                    nrow = object@style_info@legend_n_elem_row,
                    title = object@style_info@legend_title
                )
            )
        # Set the Title
        if (object@style_info@title != "") {
            plot <- plot + ggtitle(object@style_info@title)
        }
        # Set the x axis title
        if (object@style_info@x_axis_name != "") {
            plot <- plot + xlab(object@style_info@x_axis_name)
        }
        # Set the y axis title
        if (object@style_info@y_axis_name != "") {
            plot <- plot + ylab(object@style_info@y_axis_name)
        }

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
                size = adjust_text_size(9.5,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(9.5,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.title.x = element_text(
                size = adjust_text_size(13,
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
                size = adjust_text_size(9.5,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            )
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
        # Set the breaks
        if (object@style_info@n_y_breaks > 0) {
            plot <- plot +
                scale_y_continuous(
                    breaks = object@style_info@y_breaks,
                    limits = c(min(object@style_info@y_breaks),
                        max(object@style_info@y_breaks)),
                    oob = scales::squish
                )
        }

        plot
    }
)