source("plots/src/plot_impl/barplot/styles/Barplot_default.R")

# Define the derived class Barplot_default
setClass("Barplot_naive",
    contains = "Barplot_default"
)

setMethod(
    "apply_style",
    signature(object = "Barplot_naive", plot = "ggplot"),
    function(object, plot) {
        # Call parent method
        plot <- callNextMethod()
        # Calculate the colors that will be applied
        # for labels depending on its background
        # TODO-Note: using plasma but should be configurable
        colors <-
            farver::decode_colour(
                viridisLite::plasma(
                    length(
                        object@plot_info@data_frame[[object@plot_info@conf_z]]
                    ),
                    direction = -1,
                    end = 0.65
                ),
                "rgb",
                "hcl"
            )
        label_col <- ifelse(colors[, "l"] > 50, "black", "white")
        # Assign the colors to plot and labels to legend in case
        # legend names are specified
        # Remove the fill scale or an error will pop up
        i <- which(sapply(plot$scales$scales,
            function(x) "fill" %in% x$aesthetics))
        plot$scales$scales[[i]] <- NULL
        if (object@style_info@n_legend_names != 0) {
            plot <- plot +
                scale_fill_viridis_d(
                    option = "plasma",
                    labels = object@style_info@legend_names,
                    end = 0.65,
                    direction = -1
                )
        } else {
            plot <- plot +
                scale_fill_viridis_d(
                    option = "plasma",
                    end = 0.65,
                    direction = -1
                )
        }
        # Set the color of the labels
        i <- which(sapply(plot$scales$scales,
            function(x) "colour" %in% x$aesthetics))
        plot$scales$scales[[i]] <- NULL
        plot <- plot +
            scale_color_manual(
                values = label_col
            )
        plot
    }
)