#' @title Plot text size
#' @description This class is used to create a text size object
#' that will be used to format the size of the text in a plot.
#' The size of the text will be adjusted based on the dimensions
#' of the plot, width and height, and the unit format.

# Include the text size class
source("src/utils/R_structs/text_size.R")
if (!exists("Plot_text_size")) {
    # Class for the size of the text in a plot. This class
    # will only format the size depending on the size of the
    # plot, width and height, and the unit format.
    setClass("Plot_text_size",
        slots = c(
            plot_width = "numeric",
            plot_height = "numeric"
        ),
        # Inherit from the Text_size class
        contains = "Text_size",
        prototype = list(
            plot_width = 1,
            plot_height = 1
        )
    ) -> Plot_text_size

    #### METHOD DEFINITIONS ####

    setMethod("get_size",
        signature = "Plot_text_size",
        definition = function(object) {
            # Get the size of the text
            object@text_size
        }
    )

    setMethod("get_unit",
        signature = "Plot_text_size",
        definition = function(object) {
            # Get the unit format of the text
            object@unit
        }
    )

    setMethod("get_size_format",
        signature = "Plot_text_size",
        definition = function(object) {
            # Get the size of the text with format
            paste0(get_size(object), get_unit(object))
        }
    )

    setMethod("to_string",
        signature = "Plot_text_size",
        definition = function(object) {
            # Transform the text size to a string
            get_size_format(object)
        }
    )

    setMethod("calculate_size",
        signature = "Plot_text_size",
        definition = function(object) {
            object <- callNextMethod()
            # Calculate a size based on the dimensions of the plot
            # The units for the dimensions of the plot are superfluous
            # as we only apply a size adjustment factor
            object@text_size <- object@text_size *
                sqrt(object@plot_width * object@plot_height) / 25
            return(object)
        }
    )

    setMethod("initialize",
        signature = "Plot_text_size",
        definition = function(.Object, plot_width = 1, plot_height = 1, ...) {
            # Initialize the Plot_text_size object
            .Object <- callNextMethod()
            .Object@plot_width <- plot_width
            .Object@plot_height <- plot_height
            return(.Object)
        }
    )

    setValidity("Plot_text_size",
        function(object) {
            is_valid <- TRUE
            # Check if plot_width is greater than 0
            if (object@plot_width <= 0) {
                is_valid <- FALSE
                message("plot_width must be a positive number > 0")
            }
            # Check if plot_height is greater than 0
            if (object@plot_height <= 0) {
                is_valid <- FALSE
                message("plot_height must be a positive number > 0")
            }
            is_valid
        }
    )
}