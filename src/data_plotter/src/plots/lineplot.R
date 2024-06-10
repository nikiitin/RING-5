source("src/data_plotter/src/plot_iface/plot.R")
# Define the S4 class for a lineplot
setClass("lineplot", contains = "Plot")

setMethod("initialize",
  "lineplot",
  function(.Object, args) {
    .Object <- callNextMethod()
    .Object@info@data_frame %<>%
        bind_cols(.Object@info@data[.Object@info@faceting_var])

    facet_levels <- unique(pull(.Object@info@data, .Object@info@faceting_var))

    .Object@info@data_frame[.Object@info@faceting_var] <-
        factor(pull(.Object@info@data_frame, .Object@info@faceting_var),
        levels = facet_levels)

    .Object
  }
)

# Override create_plot method from Plot class
# need different behavior for Lineplot
setMethod("create_plot",
  signature(object = "lineplot"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Create the plot object
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@y]],
      group = .data[[object@info@conf_z]]
    ))
    # Add line to the plot
    # Add geometric points to convert to scatter lineplot
    # Add error bars to the points to show the standard deviation
    object@plot <- object@plot +
      geom_line(
        aes(linetype = .data[[object@info@conf_z]],
          color = .data[[object@info@conf_z]]),
        alpha = 0.6,
        linewidth = adjust_text_size(0.8,
                    object@styles@width,
                    object@styles@height)) +
      geom_point(
         aes(shape = .data[[object@info@conf_z]], color = .data[[object@info@conf_z]]),
         size = adjust_text_size(1.8,
                    object@styles@width,
                    object@styles@height)) +
      geom_errorbar(
        aes(ymin = object@info@data_frame[, object@info@y] -
          object@info@data_frame[, paste(object@info@y, "sd", sep = ".")],
        ymax = object@info@data_frame[, object@info@y] +
          object@info@data_frame[, paste(object@info@y, "sd", sep = ".")],
        color = .data[[object@info@conf_z]]),
        width = .3)

    # Facet by the variable specified in faceting_var
    if (length(object@info@faceting_var) > 0) {
      object@plot <- object@plot + facet_wrap(
        ~ .data[[object@info@faceting_var]], scales = "free")
    }

    # Return the plot
    object
  }
)

# Override apply_style method from Plot class
setMethod(
    "apply_style",
    signature(object = "lineplot"),
    function(object) {
        object <- callNextMethod()
        # Set the theme to be used
        object@plot <- object@plot + theme_hc()
        # Add specific configs to the theme
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                hjust = 1,
                vjust = 2,
                angle = 30,
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.ticks.x = element_blank(),
            axis.ticks.y = element_blank(),
            legend.box.margin = margin(-3, 0, -3, 0),
            legend.position = c(0.95,0.15),
            legend.justification = "right",
            legend.background = element_blank(),
            legend.box.background = element_rect(fill = "white", color = "black"),   
            axis.title.y = element_text(
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.title.x = element_text(
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            legend.title = element_text(
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(16,
                    object@styles@width,
                    object@styles@height)
            ),
            legend.key.width = unit(
                adjust_text_size(1,
                    object@styles@width,
                    object@styles@height),
                "cm"),
            legend.key.height = unit(
                adjust_text_size(1,
                    object@styles@width,
                    object@styles@height),
                "cm"),
            strip.text = element_text(
                size = adjust_text_size(
                    16,
                    object@styles@width,
                    object@styles@height
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
        if (length(object@styles@legend_names) != 0) {
            # GGplot seems to be really strange sometimes.
            # We need to do this because legends for shapes,
            # linetypes and colors is not the same even if the
            # content is...
            # Just used in case there is legend_names specified
            object@plot <- object@plot +
                labs(color = object@styles@legend_title,
                    shape = object@styles@legend_title,
                    linetype = object@styles@legend_title) +
                scale_color_viridis_d(labels = object@styles@legend_names,
                    option = "viridis", direction = 1) +
                scale_shape_discrete(labels = object@styles@legend_names) +
                scale_linetype_discrete(labels = object@styles@legend_names)
        } else {
            object@plot <- object@plot +
                scale_colour_viridis_d(
                    option = "viridis",
                    direction = 1
                )
        }
        # # Limit the y axis and assign labels to those
        # # statistics that overgo the top limit
        if (object@styles@y_limit_top > 0) {
            if (object@styles@y_limit_bot > object@styles@y_limit_top) {
                warning(paste0(
                    "Y limit bot is greater than Y limit top! ",
                    "skipping limits"
                ))
            } else if (object@styles@y_limit_bot < 0) {
                warning("Y limit bot is less than 0! skipping limits")
            } else {
                # Check if any stat goes over the top limit and
                # assign a label to it
                list_of_labels <-
                    ifelse(
                        ((object@info@data_frame[, object@info@y] >
                            object@styles@y_limit_top)),
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
                        size = adjust_text_size(3,
                            object@styles@width,
                            object@styles@height),
                        angle = 90,
                        hjust = "inward",
                        na.rm = TRUE
                    )
            }
        }
        object
    }
)