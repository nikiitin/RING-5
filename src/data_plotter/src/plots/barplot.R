source("src/data_plotter/src/plot_iface/plot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("barplot", contains = "Plot")

setMethod("pre_process",
    signature(object = "barplot"),
  function(object) {
    object <- callNextMethod()
    # Return the object
    object
  }
)

setMethod(
    "create_plot",
    signature(object = "barplot"),
    function(object) {
        object@plot <- ggplot(object@info@data_frame, aes(
            x = .data[[object@info@x]],
            y = .data[[object@info@y]],
            fill = .data[[object@info@conf_z]]
        ))
        # Add the geom_bar to the plot object
        object@plot <- object@plot + geom_bar(
            stat = "identity",
            position = "dodge",
            color = "black"
        )

        # # Add the facet grid to the plot object. Switch it in to X,
        # # this enforce style to group variables in x axis
        # design <- "BBBBBCCCCCDDDDD#EEEEEFFFFFGGGGGHHHHHIIIIIJJJJJKKKKKLLLLLMMMMMNNNNN#AAAAA"
        # if (object@info@n_faceting_vars > 0) {
        #   object@plot <- object@plot + facet_manual(
        #     ~ facet_column + .data[[object@info@x]],
        #     strip.position = "bottom",
        #     strip = strip_nested(
        #       clip = "off"
        #     ),
        #     design = design
        #   )
        # }
        # Add standard deviation error bars
        object@plot <- object@plot + geom_errorbar(
            aes(
                ymin =
                    object@info@data_frame[, object@info@y] -
                    object@info@data_frame[,
                        paste(object@info@y, "sd", sep = ".")],
                ymax = object@info@data_frame[, object@info@y] +
                    object@info@data_frame[,
                    paste(object@info@y, "sd", sep = ".")]
            ),
            width = .2,
            position = position_dodge(.9)
        )
        object
    }
)

setMethod(
    "apply_style",
    signature(object = "barplot"),
    function(object) {
        # Call parent method
        object <- callNextMethod()
        # Set the theme to be used
        object@plot <- object@plot + theme_hc()
        # Add specific configs to the theme
        axis_labels_size <- Vectorized_text_size(
                    text_size = 24,
                    unit = "pt",
                    plot_width = object@styles@width,
                    plot_height = object@styles@height,
                    num_labels =
                        length(unique(object@info@data_frame[[object@info@x]])))
        titles_size <- Plot_text_size(
            text_size = 16,
            unit = "pt",
            plot_width = object@styles@width,
            plot_height = object@styles@height
        )
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                angle = 30,
                hjust = 1,
                size = unit(get_size(axis_labels_size), "pt"),
                face = "bold"
            ),
            axis.ticks.x = element_blank(),
            axis.ticks.y = element_blank(),
            axis.text.y = element_text(
                hjust = 1,
                size = unit(get_size(axis_labels_size), "pt"),
                face = "bold"
            ),
            axis.title.y = element_text(
                size = unit(get_size(titles_size), "pt"),
                face = "bold"
            ),
            legend.position = "top",
            legend.justification = "right",
            legend.background= element_rect(fill = NA, color = "white"),
            legend.box.margin = margin(-18, 0, -16, 0),
            legend.title = element_text(
                size = unit(get_size(titles_size), "pt"),
                face = "bold"
            ),
            legend.text = element_text(
                size = unit(get_size(axis_labels_size), "pt"),
            ),
            legend.key.width = unit(
                get_size(titles_size) * 2, "pt"),
            legend.key.height = unit(
                get_size(titles_size) * 2, "pt"),
            strip.text = element_text(
                size = unit(get_size(axis_labels_size), "pt"),
                angle = 0,
                face = "bold"
            ),
            strip.placement = "outside",
            strip.background = 
                element_rect(fill = alpha('#2eabff', 0.1), color = "white"),
            panel.spacing = unit(0.1, "cm")
        )
        # Assign the colors to plot and labels to legend in case
        # legend names are specified
        if (length(object@styles@legend_names) != 0) {
            object@plot <- object@plot +
                scale_fill_viridis_d(
                    option = "viridis",
                    labels = object@styles@legend_names,
                    direction = 1
                )
        } else {
            object@plot <- object@plot +
                scale_fill_viridis_d(
                    option = "viridis",
                    direction = 1
                )
        }
        # Limit the y axis and assign labels to those
        # statistics that overgo the top limit
        if (object@styles@y_limit_top > 0) {
            if (object@styles@y_limit_bot > object@styles@y_limit_top) {
                warning(paste0(
                    "Y limit bot is greater than Y limit top! ",
                    "skipping limits"
                ))
            } else if (object@styles@y_limit_bot < 0) {
                warning("Y limit bot is less than 0! skipping limits")
            } else {
                # Calculate the colors that will be applied
                # for labels depending on its background
                # TODO-Note: using plasma but should be configurable
                colors <-
                    farver::decode_colour(
                        viridisLite::viridis(
                            length(
                                unique(
                                    object@info@data_frame[[
                                        object@info@conf_z
                                        ]])
                            ),
                            direction = 1,
                        ),
                        "rgb",
                        "hcl"
                    )
                label_col <- ifelse(colors[, "l"] > 50, "black", "white")
                # Check if any stat goes over the top limit and
                # assign a label to it
                list_of_labels <-
                    ifelse(
                        (object@info@data_frame[, object@info@y] >
                            (object@styles@y_limit_top)),
                        format(
                            round(
                                object@info@data_frame[
                                    ,
                                    object@info@y
                                ],
                                2
                            ),
                            nsmall = 2
                        ),
                        NA
                    )
                # Set the breaks and the limits
                object@plot <- object@plot +
                    scale_y_continuous(
                        breaks = object@styles@y_breaks,
                        oob = scales::squish
                    )
                object@plot <- object@plot + coord_cartesian(
                    ylim = as.numeric(
                        c(
                            object@styles@y_limit_bot,
                            object@styles@y_limit_top
                        )
                    )
                )
                # Add the labels to the plot
                object@plot <- object@plot +
                    geom_text(
                        position = position_dodge(.9),
                        aes(
                            label = list_of_labels,
                            group = .data[[object@info@conf_z]],
                            color = .data[[object@info@conf_z]],
                            y = object@styles@y_limit_top
                        ),
                        show.legend = FALSE,
                        size = get_size(titles_size),
                        angle = 90,
                        hjust = "inward",
                        na.rm = TRUE
                    )
                # Set the color of the labels
                object@plot <- object@plot +
                    scale_color_manual(
                        values = label_col
                    )
            }
        }
        object
    }
)