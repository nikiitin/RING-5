source("src/data_plotter/src/plot_iface/plot.R")

# Define the S4 class for a Heatmap
setClass("heatmap", contains = "Plot")


setMethod("initialize",
  "heatmap",
  function(.Object, args) {
    .Object <- callNextMethod()
    .Object@info@data_frame %<>%
        bind_cols(.Object@info@data[.Object@info@faceting_var])

    facet_levels <- unique(pull(.Object@info@data, .Object@info@faceting_var))

    .Object@info@data_frame[.Object@info@faceting_var] <-
        factor(pull(.Object@info@data_frame, .Object@info@faceting_var),
        levels = facet_levels)

    .Object@info@data_frame[.Object@info@faceting_var] <-
        factor(pull(.Object@info@data_frame, .Object@info@faceting_var),
        levels = facet_levels)
    .Object
  }
)

setMethod("pre_process",
    signature(object = "heatmap"),
  function(object) {
    object <- callNextMethod()
    object@info@data_frame[[object@info@conf_z]] %<>%
        factor(levels = unique(object@info@data[[object@info@conf_z]]))
    object@info@data_frame[[object@info@x]] %<>%
        factor(levels = unique(object@info@data[[object@info@x]]))
    if (object@info@show_only_mean == TRUE) {
        object@info@data_frame <- object@info@data_frame[object@info@data_frame[["benchmark_name"]] == "geomean", ]
    }
    # Return the object
    object
  }
)

# Override create_plot method from Plot class
# need different behavior for Heatmap
setMethod("create_plot",
  signature(object = "heatmap"),
  function(object) {
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@x]],
      y = .data[[object@info@conf_z]],
      fill = .data[[object@info@y]]
    ))
    # Add line to the plot
    # Add geometric points to convert to scatter Heatmap
    # Add error bars to the points to show the standard deviation
    object@plot <- object@plot +
      geom_tile(color = "black") +
      coord_fixed()
    list_of_labels <- format(round(object@info@data_frame[, object@info@y], 3), nsmall = 3)
    colors <- farver::decode_colour(
        colourvalues::colour_values(list_of_labels),
        "rgb",
        "hcl"
        )
    label_col <- ifelse(colors[, "l"] > 50, "black", "white")
    object@plot <- object@plot +
    geom_text(
      aes(
        label = list_of_labels),
        size = adjust_text_size(8.5,
          object@styles@width,
          object@styles@height),
        color = label_col)

    # Facet by the variable specified in faceting_var
    if (length(object@info@faceting_var) > 0) {
      object@plot <- object@plot + facet_wrap(
        object@info@faceting_var)
    }
    # Return the plot
    object
  }
)

# Override apply_style method from Plot class
setMethod(
    "apply_style",
    signature(object = "heatmap"),
    function(object) {
        object <- callNextMethod()
        # Set the theme to be used
        object@plot <- object@plot + theme_hc()
            object@plot <- object@plot +
                scale_fill_viridis_c(
                    option = "viridis",
                    direction = 1,
                    alpha = 0.8
                )
        # Reshape legend
        object@plot <- object@plot +
            guides(
                fill = guide_colourbar(
                    title = object@styles@legend_title,
                    ticks = FALSE,
                    breaks = c("max.", "min."),
                    barwidth = adjust_text_size(1,
                        object@styles@width,
                        object@styles@height),
                    barheight = adjust_text_size(20,
                        object@styles@width,
                        object@styles@height))
            )
                # # Add specific configs to the theme
        object@plot <- object@plot + theme(
            axis.text.x = element_text(
                hjust = 0.5,
                vjust = 0.5,
                size = adjust_text_size(25,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.title.x = element_text(
                vjust = 0.5,
                size = adjust_text_size(27,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 0.5,
                size = adjust_text_size(25,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            axis.title.y = element_text(
                hjust = 0.5,
                size = adjust_text_size(27,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            legend.position = "right",
            legend.title = element_text(
                size = adjust_text_size(25,
                    object@styles@width,
                    object@styles@height),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(23,
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
            strip.text = element_blank(),
            strip.placement = "outside",
            strip.background = element_blank(),
            panel.spacing = unit(0.1, "cm"),
            panel.grid.major.y = element_blank()
        )
        object
    }
)