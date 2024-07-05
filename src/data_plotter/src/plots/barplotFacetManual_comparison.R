source("src/data_plotter/src/plots/barplot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("barplotFacetManual_comparison", contains = "barplot")

setMethod(
    "create_plot",
    signature(object = "barplotFacetManual_comparison"),
    function(object) {
        object@plot <- ggplot(object@info@data_frame, aes(
            x = "",
            y = .data[[object@info@y]],
            fill = .data[[object@info@conf_z]]
        ))
        # Add the geom_bar to the plot object
        object@plot <- object@plot + geom_bar(
            stat = "identity",
            position = "dodge",
            color = "black"
        )
        design <- "BBBBBCCCCCDDDDD#EEEEEFFFFFGGGGGHHHHHIIIIIJJJJJKKKKKLLLLLMMMMM#AAAAA"
        if (length(object@info@faceting_var) > 0) {
          object@plot <- object@plot + facet_manual(
            ~ facet_column + .data[[object@info@x]],
            strip.position = "bottom",
            strip = strip_nested(
              clip = "off"
            ),
            design = design
          )
        }
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
    signature(object = "barplotFacetManual_comparison"),
    function(object) {
        object <- callNextMethod()
        # We need the 3rd and the last color from the palette
                color_vector <- viridis::viridis(5)
        color_vector <- color_vector[c(3, 5)]
        # Now we need to add red and light red to the color vector
        color_vector <- c(color_vector, "#BC2429")
        # Now we need to add the colors to the plot
        object@plot <- object@plot + scale_fill_manual(values = color_vector, labels = object@styles@legend_names)
        object
    }
)