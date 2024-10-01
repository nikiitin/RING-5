source("src/data_plotter/src/plot_iface/plot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("groupedStackedBarplot", contains = "Plot")

setMethod(
    "pre_process",
    signature(object = "groupedStackedBarplot"),
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
                levels = unique(object@info@data_frame$entries)
            )
        # Return the object
        object
    }
)

setMethod(
    "create_plot",
    signature(object = "groupedStackedBarplot"),
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
        total_values <- NA
        if (object@styles@y_limit_top > 0) {
            if (object@styles@y_limit_bot > object@styles@y_limit_top) {
                warning(paste0(
                    "Y limit bot is greater than Y limit top! ",
                    "skipping limits"
                ))
            } else {
                if (object@styles@y_limit_top < max(object@styles@y_breaks)) {
                    warning(paste0(
                        "Y limit top is lower than the ",
                        "maximum value of breaks!",
                    ))
                }
                total_values <- object@info@data_frame %>%
                    group_by(.data[[object@info@conf_z]],
                        .data[[object@info@x]]) %>%
                    summarise(total = sum(values), .groups = "drop")

                total_values[, "total"] <-
                    as.numeric(format(round(total_values$total, 2), nsmall = 2))

                total_values[, "total"] <-
                    ifelse(total_values$total < max(object@styles@y_limit_top),
                        NA,
                        total_values$total
                    )
            }
        }
        object@plot <- ggplot(object@info@data_frame, aes(
            x = .data[[object@info@conf_z]],
            y = values
        ))


        # Add the facet grid to the plot object. Switch it in to X,
        # this enforce style to group variables in x axis
        object@plot <- object@plot + facet_manual(
            ~ facet_column + .data[[object@info@x]],
            strip.position = "bottom",
            strip = strip_nested(
                clip = "off"
            ),
            design = create_facet_design(object, 5, c("Microbenchmark", "STAMP", "(STAMP)"))
        )

        # Add the geom_bar to the plot object. Use position_stack to
        # stack the bars and reverse = TRUE to have the bars in the
        # same order as the legend.
        object@plot <- object@plot + geom_col(
            aes(fill = entries),
            position = position_stack(reverse = TRUE),
            color = "black"
        )



        if (!all(is.na(total_values$total))) {
            # If all values are NA, do not add the text
            # or it will throw an error
            object@plot <- object@plot + geom_text(
                data = total_values,
                aes(
                    y = total,
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
        # REALLY UGLY, I do not know if it
        # should be used, just let it here, maybe it is useful

        # # Add standard deviation error bars, use the caculated
        # # error_bar as y axis
        # object@plot <- object@plot + geom_errorbar(
        #   data = error_df,
        #   aes(
        #     ymin = error_bar_cumsum - values_sd,
        #     ymax = error_bar_cumsum + values_sd,
        #   ),
        #   width = .2
        # )


        # Return the plot
        object
    }
)

setMethod(
    "apply_style",
    signature(object = "groupedStackedBarplot"),
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
        axis_labels_size <- Vectorized_text_size(
            text_size = 34,
            unit = "pt",
            plot_width = object@styles@width,
            plot_height = object@styles@height,
            num_labels =
                length(unique(object@info@data_frame[[object@info@x]]))
        )
        titles_size <- Plot_text_size(
            text_size = 20,
            unit = "pt",
            plot_width = object@styles@width,
            plot_height = object@styles@height
        )
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                angle = 45,
                hjust = 1,
                size = unit(get_size(axis_labels_size), "pt"),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = unit(get_size(axis_labels_size), "pt"),
                face = "bold"
            ),
            axis.title.x = element_blank(),
            axis.title.y = element_text(
                size = unit(get_size(titles_size), "pt"),
                face = "bold"
            ),
            # legend.position = c(0.8,0.9),
            legend.position = "top",
            legend.justification = "right",
            # legend.background = element_blank(),
            # legend.box.background = element_rect(fill = "white", color = "black"),
            legend.title = element_text(
                size = unit(get_size(titles_size), "pt"),
                face = "bold"
            ),
            legend.text = element_text(
                size = unit(get_size(titles_size), "pt")
            ),
            legend.key.width = unit(
                get_size(titles_size) * 1.2, "pt"),
            legend.key.height = unit(
                get_size(titles_size) * 1.2, "pt"),
            legend.box.margin = margin(-3, 0, -3, 0),
            strip.text = element_text(
                size = unit(get_size(axis_labels_size), "pt"),
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
                        object@styles@y_limit_bot,
                        object@styles@y_limit_top
                    ),
                    oob = scales::squish,
                    expand = c(0, 0)
                )
        }
        object
    }
)