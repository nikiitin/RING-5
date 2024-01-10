source("plots/src/plot_impl/barplot/styles/Barplot_default.R")
source("plots/src/plot_impl/stackedbarplot/styles/info/stackedBarplotStyleInfo.R")

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
        # Set the breaks
        if (object@style_info@n_y_breaks > 0) {
            plot <- plot +
                scale_y_continuous(
                    breaks = object@style_info@y_breaks,
                    oob = scales::squish
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
                # Warn the user about using limits on stacked barplots
                warning("Y limits are not recommended for stacked barplots")
                warning("Won't be applied!")
            }
        }
        plot
    }
)