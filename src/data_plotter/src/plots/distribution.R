source("src/data_plotter/src/plot_iface/plot.R")
# Define the S4 class for a lineplot
every_nth = function(n) {
  return(function(x) {x[c(TRUE, rep(FALSE, n - 1))]})
}
setClass("distribution", contains = "Plot")

setMethod("initialize",
  "distribution",
  function(.Object, args) {
    .Object@args <- args
    ## Args parse ##
    # Create plotInfo object
    .Object@info <- new("Plot_info",
      args = .Object@args
    )
    # Update args to remove the ones already used
    .Object %<>% update_args(.Object@info@args)
    .Object@styles <- new("Plot_style",
      args = .Object@args
    )
    # Update args
    .Object %<>% update_args(.Object@styles@args)
    # X is not used
    # Add conf_z columns
    .Object@info@data_frame <- .Object@info@data[.Object@info@conf_z]
    # Take into account that conf_z column is an already ordered factor
    # so assign back the levels to the data frame
    .Object@info@data_frame[, .Object@info@conf_z] %<>%
      factor(levels = unique(.Object@info@data[, .Object@info@conf_z]))
    ## Data formating ##
    cols_to_include <- grep(.Object@info@y, colnames(.Object@info@data), value=TRUE)
    .Object@info@data_frame %<>% cbind(.Object@info@data[cols_to_include])

    .Object@info@data_frame %<>%
        cbind(.Object@info@data[.Object@info@faceting_var])
    .Object@info@data_frame %<>% 
        select(-tidyselect::ends_with(".sd")) %>%
        pivot_longer(
        cols = starts_with(.Object@info@y),
        names_to = "dist_names",
        values_to = "dist_vals",
        names_pattern = "^.*?\\.\\.(\\.?.*)"
    )
    .Object@info@data_frame$dist_names %<>% str_replace("^\\.", "-")
    
    numeric_values <- as.numeric(unique(.Object@info@data_frame$dist_names))
    numeric_values <- numeric_values[!is.na(numeric_values)]

    numeric_ranges <- cut(numeric_values, breaks = 16)
    range_names <- as.character(numeric_ranges)
    # Reemplaza los valores numéricos en dist_names con los nombres de los rangos
    .Object@info@data_frame$dist_names[.Object@info@data_frame$dist_names %in% numeric_values] <- range_names

    # Agrupa por dist_names y suma dist_vals
.Object@info@data_frame <- .Object@info@data_frame %>%
  group_by(dist_names, .data[[.Object@info@conf_z]], .data[[.Object@info@faceting_var]]) %>%
  summarise(dist_vals = sum(dist_vals), .groups = "keep")


    # Desagrupa el dataframe
    .Object@info@data_frame <- ungroup(.Object@info@data_frame)



# # Reemplaza los valores numéricos en dist_names con los nombres de los rangos
# .Object@info@data_frame$dist_names[.Object@info@data_frame$dist_names %in% numeric_values] <- range_names
    .Object@info@data_frame$dist_names <-
        factor(.Object@info@data_frame$dist_names,
        levels = c("underflows", unique(range_names), "overflows"))

    .Object
  }
)


# Override create_plot method from Plot class
# need different behavior for Lineplot
setMethod("create_plot",
  signature(object = "distribution"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Create the plot object

    object@plot <- ggplot(object@info@data_frame, aes(
      x = dist_names,
      y = dist_vals,
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
                    object@styles@height))

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
    signature(object = "distribution"),
    function(object) {
        object <- callNextMethod()
        # Set the theme to be used
        object@plot <- object@plot + theme_hc()
        # Add specific configs to the theme
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                hjust = 1,
                vjust = 1,
                angle = 30,
                size = adjust_text_size(8,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 1,
                size = adjust_text_size(8,
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
                    ) +
                    scale_x_discrete(breaks = every_nth(4))
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