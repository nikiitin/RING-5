#' @title Vectorized_text_size
#' @description This class is used to create a text size object
#' that will be used to format the size of the text in a vectorized plot.
#' The size of the text will be adjusted based on the number of labels
#' and the unit format.
if (!exists("Vectorized_text_size")) {
    source("src/utils/R_structs/text_sizes/plot_text_size.R")
    # Class for the size of the text in a vectorized plot.
    setClass("Vectorized_text_size",
        # Inherit from the Plot_text_size class
        contains = "Plot_text_size",
        slots = list(
            # The number of labels
            num_labels = "numeric"
        )
    ) -> Vectorized_text_size

    setValidity("Vectorized_text_size",
        function(object) {
            is_valid <- TRUE
            # Check if the number of labels is positive
            if (object@num_labels <= 0) {
                message("The number of labels must be a positive number > 0")
                is_valid <- FALSE
            }
            is_valid
        }
    )

    setMethod("calculate_size",
        signature = "Vectorized_text_size",
        definition = function(object) {
            object <- callNextMethod()
            # Add the number of labels to the conversion factor
            # Make the text size smaller proportional to the number of labels
            object@text_size <- object@text_size /
                (0.15 * object@num_labels)
            return(object)
        }
    )

    setMethod(
        "initialize", "Vectorized_text_size",
        function(.Object, num_labels = 1, ...) {
            .Object <- callNextMethod()
            .Object@num_labels <- num_labels
            return(.Object)
        }
    )
}