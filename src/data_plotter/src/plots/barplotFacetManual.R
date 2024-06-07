source("src/data_plotter/src/plot_iface/plot.R")
# This is the definition for the barplot type. It is inheriting
# from the Plot class.

setClass("barplotFacetManual", contains = "barplot")

setMethod(
    "create_plot",
    signature(object = "barplot"),
    function(object) {
        object <- callNextMethod()
        design <- "BBBBBCCCCCDDDDD#EEEEEFFFFFGGGGGHHHHHIIIIIJJJJJKKKKKLLLLLMMMMMNNNNN#AAAAA"
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
        object
    }
)