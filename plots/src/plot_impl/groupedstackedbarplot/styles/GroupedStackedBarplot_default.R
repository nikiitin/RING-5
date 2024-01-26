source("plots/src/plot_impl/stackedbarplot/styles/StackedBarplot_default.R")
source("plots/src/plot_impl/groupedstackedbarplot/styles/info/groupedStackedBarplotInfo.R")

# Define the derived class Barplot_default
setClass("GroupedStackedBarplot_default",
    contains = "StackedBarplot_default"
)

# Create_style_info with Barplot info
setMethod(
    "create_style_info",
    signature(object = "GroupedStackedBarplot_default"),
    function(object) {
        # Create barplot style info object
        # It will define which variables will be used
        # stick to it in the rest of the styles for this kind
        # of plot
        object@style_info <- new("GroupedStackedBarplot_style_info",
            args = object@args
        )
        # Return the object
        object
    }
)


setMethod(
    "apply_style",
    signature(object = "GroupedStackedBarplot_default", plot = "ggplot"),
    function(object, plot) {
        # Call parent and return
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
        # Label x axis with the legend names if specified
        # Label names were conf_z names on other plots
        if (object@style_info@n_legend_names > 0) {
            plot <- plot + scale_x_discrete(
                labels = object@style_info@legend_names,
            )
        }

        # x split points
        if (object@style_info@n_x_split_points > 0) {
            # A bit tricky here. Using vlines in facets replicate the
            # line for each facet and xintercept match x INSIDE every facet.
            # x split points are meant to split only once the x axis
            # Get x variables, map the xsplit points to the matching variable
            # and put that in a data frame (other data source)
            # with the x being the x value we want to intercept (FACET)
            # and xint being the x inside the facet where we want to
            # put the line
            x_variables <-
                unique(object@plot_info@data_frame[[object@plot_info@x]])
            x_split_points <-
                floor(
                    as.numeric(
                        object@style_info@x_split_points
                        )
                    )
            x_index <- x_variables[[x_split_points]]
            z_variables <-
                unique(object@plot_info@data_frame[[object@plot_info@conf_z]])
            mapping <- data.frame(
                xint = length(z_variables) + 0.5,
                x = x_index
            )
            colnames(mapping) <- c("xint", object@plot_info@x)
            plot <- plot +
                geom_vline(data = mapping,
                    aes(xintercept = xint),
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
                size = adjust_text_size(11.5,
                    object@style_info@width,
                    object@style_info@height),
                angle = 30,
            ),
            strip.clip = "off",
            strip.placement = "outside",
            strip.background = element_rect(fill = NA, color = "white"),
            panel.spacing = unit(0.1, "cm")
        ) # Added facet specific configs

        # Assign the colors to plot
        plot <- plot +
            scale_fill_viridis_d(
                option = "plasma",
                direction = -1
            )

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