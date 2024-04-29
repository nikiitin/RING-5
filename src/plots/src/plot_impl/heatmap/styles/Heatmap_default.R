library(prismatic)
library(ggthemes)
source("src/plots/src/plot_impl/heatmap/styles/info/heatmapStyleInfo.R")

# Define the derived class Heatmap_default
setClass("Heatmap_default",
    contains = "Plot_style"
)

# Create_style_info with Heatmap info
setMethod(
    "create_style_info",
    signature(object = "Heatmap_default"),
    function(object) {
        # Create Heatmap style info object
        # It will define which variables will be used
        # stick to it in the rest of the styles for this kind
        # of plot
        object@style_info <- new("Heatmap_style_info",
            args = object@args
        )
        # Return the object
        object
    }
)
setMethod(
    "check_data_correct",
    signature(object = "Heatmap_default"),
    function(object) {

    }
)


# Override all needed methods from the plot_format class
# Overriding initialize method from plot_format class
setMethod(
    "initialize",
    signature(.Object = "Heatmap_default"),
    function(.Object, plot_info, args) {
        # Call parent method
        .Object <- callNextMethod()
        # Return the object
        .Object
    }
)

setMethod(
    "apply_style",
    signature(object = "Heatmap_default", plot = "ggplot"),
    function(object, plot) {
        # Set the theme to be used
        plot <- plot + theme_hc()
        # # Assign the colors to plot and labels to legend in case
        # # legend names are specified
        # if (object@style_info@n_legend_names != 0) {
        #     # GGplot seems to be really strange sometimes.
        #     # We need to do this because legends for shapes,
        #     # linetypes and colors is not the same even if the
        #     # content is...
        #     # Just used in case there is legend_names specified
        #     plot <- plot +
        #         labs(color = object@style_info@legend_title,
        #             shape = object@style_info@legend_title,
        #             linetype = object@style_info@legend_title) +
        #         scale_color_viridis_d(labels = object@style_info@legend_names,
        #             option = "viridis", direction = 1) +
        #         scale_shape_discrete(labels = object@style_info@legend_names) +
        #         scale_linetype_discrete(labels = object@style_info@legend_names)
        # } else {
            plot <- plot +
                scale_fill_viridis_c(
                    option = "viridis",
                    direction = 1,
                    alpha = 0.8
                )
        
 
        #         # Calculate the colors that will be applied
        #         # for labels depending on its background
        #         # TODO-Note: using plasma but should be configurable
        #         colors <-
        #             farver::decode_colour(
        #                 viridisLite::viridis(
        #                     length(
        #                         unique(object@plot_info@data_frame[[object@plot_info@conf_z]])
        #                     ),
        #                     direction = 1,
        #                 ),
        #                 "rgb",
        #                 "hcl"
        #             )
        #         label_col <- ifelse(colors[, "l"] > 50, "black", "white")
                # Check if any stat goes over the top limit and
                # assign a label to it
                # list_of_labels <-
                #     ifelse(
                #         ((object@plot_info@data_frame[, object@plot_info@y] >
                #             object@style_info@y_limit_top)),
                #         format(
                #             round(
                #                 object@plot_info@data_frame[
                #                     ,
                #                     object@plot_info@y
                #                 ],
                #                 2
                #             ),
                #             nsmall = 2
                #         ),
                #         NA
                #     )
                # # Set the breaks and the limits
        plot <- callNextMethod()
        # Reshape legend
        plot <- plot +
            guides(
                fill = guide_colourbar(
                    title = object@style_info@legend_title,
                    ticks = FALSE,
                    breaks = c("max.", "min."),
                    barwidth = adjust_text_size(1,
                        object@style_info@width,
                        object@style_info@height),
                    barheight = adjust_text_size(20,
                        object@style_info@width,
                        object@style_info@height))
            )
                # # Add specific configs to the theme
        plot <- plot + theme(
            axis.text.x = element_text(
                hjust = 0.5,
                vjust = 0.5,
                size = adjust_text_size(25,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.title.x = element_text(
                vjust = 0.5,
                size = adjust_text_size(27,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.text.y = element_text(
                hjust = 0.5,
                size = adjust_text_size(25,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            axis.title.y = element_text(
                hjust = 0.5,
                size = adjust_text_size(27,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            legend.position = "right",
            legend.title = element_text(
                size = adjust_text_size(25,
                    object@style_info@width,
                    object@style_info@height),
                face = "bold"
            ),
            legend.text = element_text(
                size = adjust_text_size(23,
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
            strip.text = element_blank(),
            strip.placement = "outside",
            strip.background = element_blank(),
            panel.spacing = unit(0.1, "cm"),
            panel.grid.major.y = element_blank()
        )
        plot
    }
)