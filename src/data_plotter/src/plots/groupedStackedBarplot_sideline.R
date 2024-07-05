source("src/data_plotter/src/plot_iface/plot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("groupedStackedBarplot_sideline", contains = "Plot",
    slots = list(
        # The data frame to be sidely plotted
        side_data = "data.frame"
    )
)

setMethod(
    "pre_process",
    signature(object = "groupedStackedBarplot_sideline"),
    function(object) {
        object <- callNextMethod()
        # The vector ID is kept in csv to avoid collisions
        # There is a common part of the name of the columns that is
        # the same for all the entries. We need to remove it
        # to have only the name of the entries
        # Remove vector ID as all collisions are already removed
        # while adding elements to the data frame
        object@info@data_frame %<>%
            dplyr::rename_with(
                ~ sub(".*\\.\\.", "", .)
            )
        # We want to get the data frame for variables with __side
        # modifier
        object@side_data <- object@info@data_frame[
            c(object@info@x, object@info@conf_z, "facet_column")]
        if (object@info@data_frame %>%
            select(ends_with("__side")) %>% ncol() > 2) {
            # More variables than allowed, side is a simple geom_line
            # and we do not want to add too much visual complexity
            # to the plot
            stop("Error: Side data is lineplot and cannot have more than 1 variable")
        } else if (object@info@data_frame %>%
            select(ends_with("__side")) %>% ncol() == 0) {
            # No side data, no need to do anything
            stop("Error: No side data found, use groupedStackedBarplot instead")
        }
        object@side_data %<>% cbind(object@info@data_frame %>%
            select(ends_with("__side"))
            )
        # Standard deviation of course :)
        side_sd_df <- object@info@data_frame %>%
            select(ends_with("__side.sd"))
        # Now remove all the columns that appear in those
        # data frames and that would be all
        object@info@data_frame <- object@info@data_frame %>%
            select(-ends_with("__side"), -ends_with("__side.sd"))
        # Add the standard deviation to the side data
        object@side_data <- cbind(object@side_data, side_sd_df)

        sd_df <- object@info@data_frame %>% tidyr::pivot_longer(
            cols = tidyselect::ends_with(".sd"),
            names_to = "entries",
            values_to = "values_sd"
        )
        object@info@data_frame %<>%
            select(-tidyselect::ends_with(".sd")) %>%
            tidyr::pivot_longer(
                cols = -c(object@info@x, object@info@conf_z, facet_column),
                names_to = "entries",
                values_to = "values"
            ) %>%
            cbind(values_sd = sd_df$values_sd)
        
        object@info@data_frame$entries <-
            factor(object@info@data_frame$entries,
            levels = unique(object@info@data_frame$entries))
        # Return the object
        object
    }
)

setMethod(
    "create_plot",
    signature(object = "groupedStackedBarplot_sideline"),
    function(object) {
        # Get the cummulative sum of the y axis. It will be used
        # to set error bars for each entry
        # Just let it here, in case it is useful
        # error_df <- object@info@data_frame %>%
        #   group_by(conf_z,x) %>%
        #   mutate(error_bar_cumsum = cumsum(values)) %>%
        #   ungroup()

        # Data mapping performed here is hard to understand but
        # it would summarize to something like this:
        #        |
        # y_val  |
        #        |
        #        |
        #        -----------------------
        #        |                     |
        #     conf_z_a              conf_z_b
        #        |                     |
        #        -----------------------
        #                  X
        # Names from df should be always the same, it is a wrap
        # specific for this plot
        plots <- list()
        # We will need to track the current facetting count
        current_facet <- 1
        current_plot <- 1
        first <- TRUE
        for (element in unique(object@info@data_frame$facet_column)) {
            # For each different facet
            # Create a plot
            # Have into account that stacked plots have conf_z
            # as the x axis and aesthetic
            # X are each of the facets
            local_plot <- ggplot(object@info@data_frame %>%
                filter(facet_column == element),
                aes(
                    x = .data[[object@info@conf_z]],
                    y = values
                ))
            # Now do the facet for X axis
            local_plot <- local_plot + facet_manual(
                ~ facet_column + .data[[object@info@x]],
                strip.position = "bottom",
                strip = strip_nested(
                    clip = "off"
                ),
                # Design fixed to have 5 spaces per facet
                design = create_facet_design(object, 5, element, current_facet)
            )
            current_facet <- current_facet + sum(
                object@info@data_frame %>%
                    filter(facet_column == element) %>%
                    select(.data[[object@info@x]]) %>%
                    distinct() %>% nrow()

            )
            # Add the plotting representation
            # Add the geom_bar to the plot object. Use position_stack to
            # stack the bars and reverse = TRUE to have the bars in the
            # same order as the legend.
            local_plot <- local_plot + geom_col(
                aes(fill = entries),
                position = position_stack(reverse = TRUE),
                color = "black"
            )
            # Get the elements from the side_df
            # That apply for this facet
            side_df <- object@side_data %>%
                filter(facet_column == element)
            # Get the column that contains the points
            # needed for the side plot
            y_points_side <- side_df %>%
                select(ends_with("__side")) %>%
                colnames()
            
            #### Side plot ####
            # Add points and lines for the side data
            local_plot <- local_plot + geom_point(
                data = side_df,
                aes(x = .data[[object@info@conf_z]],
                y = .data[[y_points_side]]),
                color = "red",
                size = adjust_text_size(2.4,
                        object@styles@width,
                        object@styles@height)) +
            geom_line(data = side_df,
                aes(x = .data[[object@info@conf_z]],
                    y = .data[[y_points_side]],
                    group = facet_column),
                color = "red",
                linewidth = adjust_text_size(0.5,
                    object@styles@width,
                    object@styles@height))
            #### End of side plot ####
            print(side_df)
            total_side_values <- side_df %>%
                group_by(.data[[object@info@conf_z]], .data[[object@info@x]]) %>%
                summarise(total = .data[[y_points_side]], .groups = "drop")
            
            # Round labelling to two decimals
            total_side_values[, "total"] <-
                as.numeric(format(round(total_side_values$total, 2), nsmall = 2))
            # Put the label only if the total is greater than the
            # maximum value of the breaks in the y axis
            total_side_values[, "total"] <-
                ifelse(total_side_values$total < max(object@styles@y_breaks),
                    NA,
                    total_side_values$total)

            # print(total_side_values)
            # print(side_df)
            # Get the totals for labeling on this plot
            total_values <- object@info@data_frame %>%
                filter(facet_column == element) %>%
                group_by(.data[[object@info@conf_z]], .data[[object@info@x]]) %>%
                summarise(total = sum(values), .groups = "drop")
            # Round labelling to two decimals
            total_values[, "total"] <-
                as.numeric(format(round(total_values$total, 2), nsmall = 2))
            # Put the label only if the total is greater than the
            # maximum value of the breaks in the y axis
            total_values[, "total"] <-
                ifelse(total_values$total < max(object@styles@y_breaks),
                    NA,
                    total_values$total)
            # print(total_values)
            # Labelling
            if (!all(is.na(total_values$total))) {
                # If all values are NA, do not add the text
                # or it will throw an error
                local_plot <- local_plot + geom_text(
                    data = total_values,
                    aes(
                        y = max(object@styles@y_breaks),
                        label = total,
                        x = .data[[object@info@conf_z]]
                    ),
                    color = "white",
                    angle = 90,
                    hjust = "inward",
                    na.rm = TRUE,
                    size = adjust_text_size(
                        5,
                        object@styles@width,
                        object@styles@height
                    ),
                    position = position_dodge(width = 1)
                )
            }
            if (!all(is.na(total_side_values$total))) {
                # If all values are NA, do not add the text
                # or it will throw an error
                local_plot <- local_plot + geom_text_repel(
                    data = total_side_values,
                    aes(
                        y = max(object@styles@y_breaks),
                        label = total,
                        x = .data[[object@info@conf_z]]
                    ),
                    color = "red",
                    angle = 90,
                    hjust = "inward",
                    na.rm = TRUE,
                    size = adjust_text_size(
                        4,
                        object@styles@width,
                        object@styles@height
                    ),
                    position = position_dodge(width = 1)
                )
            }
            
            if (first) {
                # If it is the first plot, assign it to the object
                plots[[current_plot]] <- local_plot 
                first <- FALSE
            } else {
                # If it is not the first plot, add it to the patchwork
                plots[[current_plot]] <- local_plot
            }
            current_plot <- current_plot + 1
        }

        # Calculate the width for each plot
        # The width is proportional to the amount
        # of facets each plot has
        # The width is calculated as the number of facets
        # divided by the total number of facets
        # The width is then multiplied by the total width
        # of the plot
        widths <- object@info@data_frame %>%
            group_by(facet_column) %>%
            summarise(n = n(), .groups = "drop") %>%
            mutate(width = n / sum(n) * object@styles@width) %>%
            pull(width)

        # Create the patchwork object
        object@plot <- patchwork::wrap_plots(plots)

        object@plot <- object@plot +
            plot_layout(
                widths = widths,
                guides = "collect",
                axis_titles = "collect",
                axes = "collect_y"
            )


        # Return the plot
        object
    }
)

setMethod(
    "apply_style",
    signature(object = "groupedStackedBarplot_sideline"),
    function(object) {
        # Apply style to the plot
        # Set the number of elements per row in the legend
        # and the title of the legend
        object@plot <- object@plot &
            guides(
                fill = guide_legend(
                    nrow = object@styles@legend_n_elem_row,
                    title = object@styles@legend_title,
                    title.position = "left"
                )
            )

        # Set the Title
        if (object@styles@title != "") {
            object@plot <- object@plot & ggtitle(object@styles@title)
        }
        # Set the x axis title
        if (object@styles@x_axis_name != "") {
            object@plot <- object@plot & xlab(object@styles@x_axis_name)
        }
        # Set the y axis title
        if (object@styles@y_axis_name != "") {
            object@plot <- object@plot & ylab(object@styles@y_axis_name)
        }
        # Label x axis with the legend names if specified
        # Label names were conf_z names on other plots
        if (length(object@styles@legend_names) > 0) {
            object@plot <- object@plot & scale_x_discrete(
                labels = object@styles@legend_names
            )
        }

        # Set the theme to be used
        object@plot <- object@plot & theme_hc()
        # Add specific configs to the theme
        object@plot <- object@plot & theme(
            axis.text.x = element_text(
                angle = 45,
                hjust = 1,
                size = adjust_text_size(
                    8,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            axis.title.x = element_blank(),
            axis.title.y = element_text(
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            axis.text.y.right = element_text(
                hjust = 1,
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold",
                color = "red"
            ),
            axis.title.y.right = element_text(
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold",
                color = "red"
            ),
            # legend.position = c(0.8,0.9),
            legend.position = "top",
            legend.justification = "right",
            legend.background = element_blank(),
            legend.box.background = element_rect(fill = "white", color = "black"),
            legend.title = element_text(
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                ),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(
                    13,
                    object@styles@width,
                    object@styles@height
                )
            ),
            legend.key.width = unit(
                adjust_text_size(
                    0.7,
                    object@styles@width,
                    object@styles@height
                ),
                "cm"
            ),
            legend.key.height = unit(
                adjust_text_size(
                    0.7,
                    object@styles@width,
                    object@styles@height
                ),
                "cm"
            ),
            legend.box.margin = margin(-3, 0, -3, 0),
            strip.text = element_text(
                size = adjust_text_size(
                    13,
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
        color_index_vector <- get_stack_discrete_color_vector(
            length(unique(object@info@data_frame$entries))
            )
        # Get the colors from the viridis palette
        color_vector <- viridis::viridis(length(color_index_vector))
        # color_vector <- viridis::viridis(
        #     length(unique(object@info@data_frame$entries))
        # )
        # Apply the specific order from the color index vector
        color_vector <- color_vector[color_index_vector * (length(color_vector) - 1) + 1]
        object@plot <- object@plot &
            scale_fill_manual(
                values = color_vector
            )

        # Set the breaks
        if (length(object@styles@y_breaks) > 0) {
            object@plot <- object@plot &
                scale_y_continuous(
                    breaks = object@styles@y_breaks,
                    oob = scales::oob_squish,
                    expand = c(0, 0.03),
                    sec.axis = sec_axis(
                        ~ .,
                        breaks = object@styles@y_breaks,
                        name = "Aborts(Normalized)"
                    )
                )
        }

    object@plot <- object@plot & coord_cartesian(
        ylim = as.numeric(
            c(
                min(object@styles@y_breaks),
                max(object@styles@y_breaks)
                )
            )
        )
        object
    }
)