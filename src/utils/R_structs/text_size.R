#' @title Text size class
#' @description This class is used to create a text size object
#' that will be used to format the size of a text.
#' The size of the text will be adjusted based on the unit format.
#' The unit format can be "pt", "px", "mm", "cm" or "in".
#' The size of the text will be calculated depending on the unit format.
#' This is an interface class, so it will not implement the
#' functionality
if (!exists("Text_size")) {
    # Check if the file is already sourced
    # Define the S4 class for a generic text size
    setClass("Text_size",
        # Define the fields of the class
        slots = list(
            # Put all parameters here!
            text_size = "numeric",
            unit = "character"
        ),
        # Define the prototype of the class
        prototype = list(
            text_size = 1,
            unit = "pt"
        ),
    ) -> Text_size
    # METHOD DECLARATIONS
    #### GENERIC METHOD DEFINITIONS ####

    #' Get the size of the text
    #'
    #' Getter method to get the size of the text
    #' without the unit format. It will calculate
    #' the size, depending on different factors, like
    #' the size of the plot, what kind of text it is
    #' (title, subtitle, axis, etc), and the unit format.
    #'
    #' @param object The text size object
    #' @return The size of the text without the unit
    #' @seealso [get_size_format(), get_unit(), to_string(),
    #' calculate_size()]
    #' @export
    setGeneric("get_size", function(object) {
        standardGeneric("get_size")
    })

    #' Get the size of the text with format
    #'
    #' Getter method to get the size of the text
    #' with the unit format. Note that the return
    #' value is a string.
    #'
    #' @param object The text size object
    #' @return The size of the text and the unit
    #' @seealso [get_size(), get_unit(), to_string(),
    #' calculate_size()]
    #' @export
    setGeneric("get_size_format", function(object) {
        standardGeneric("get_size_format")
    })

    #' Get the format unit of the text
    #'
    #' Getter method for the unit format of the text.
    #' The unit format is the unit that will be used
    #' to represent the size of the text. It can be
    #' "pt", "px", "mm", "cm" or "in"
    #'
    #' @param object The text size object
    #' @return The size of the text and the unit
    #' @seealso [get_size(), get_size_format(), to_string(),
    #' calculate_size()]
    #' @export
    setGeneric("get_unit", function(object) {
        standardGeneric("get_unit")
    })

    #' Transform the text size to a string
    #'
    #' This method is used to transform the text size
    #' to a string. The string will contain the size
    #' and the unit format. This method is useful to
    #' print the text size in a human readable format.
    #'
    #' @param object The text size object
    #' @return The size of the text and the unit in a string
    #' @seealso [get_size(), get_size_format(), get_unit(),
    #' calculate_size()]
    setGeneric("to_string", function(object) {
        standardGeneric("to_string")
    })

    #' Calculate the size of the text
    #'
    #' This method is used to calculate the size of the text
    #' depending on different factors that can affect the size
    #' of the text. These factors will be specified in the
    #' implementation of this method.
    #'
    #' @param object The text size object
    #' @return The size of the text
    #' @seealso [get_size(), get_size_format(), get_unit(),
    #' to_string()]
    setGeneric("calculate_size", function(object) {
        standardGeneric("calculate_size")
    })

    setValidity(
        "Text_size",
        function(object) {
            is_valid <- TRUE
            # Check if the text size is a positive number
            if (object@text_size <= 0) {
                is_valid <- FALSE
                message("text_size must be a positive number > 0")
            }
            # Check if the unit is a valid unit
            if (!(object@unit %in% c("pt", "px", "mm", "cm", "in"))) {
                is_valid <- FALSE
                message(paste0("The text size unit must be ", 
                    "one of the following: pt, px, mm, cm, in"))
            }
            # If all checks pass, return TRUE
            return(is_valid)
        }
    )

    # This method should only be used by the
    # child classes of Text_size. It will
    # calculate the size of the text depending
    # on the unit format. It will only do a simple
    # and automatic conversion between the different units.
    setMethod(
        "initialize", "Text_size",
        function(.Object, text_size = 1, unit = "pt", ...) {
            # Call the parent class constructor
            .Object <- callNextMethod()
            # Set the text size
            .Object <- calculate_size(.Object)
            # Set the unit format
            .Object@unit <- unit
            return(.Object)
        }
    )

    setMethod("calculate_size",
        signature = "Text_size",
        definition = function(object) {
            # Calculate the size of the text
            # depending on the format. This is a simple
            # conversion between the different units.
            if (object@unit == "pt") {
                # Calculate the size in points
                object@text_size
            } else if (object@unit == "px") {
                # Calculate the size in pixels
                object@text_size * 0.75
            } else if (object@unit == "mm") {
                # Calculate the size in millimeters
                object@text_size * 2.83465
            } else if (object@unit == "cm") {
                # Calculate the size in centimeters
                object@text_size * 28.3465
            } else if (object@unit == "in") {
                # Calculate the size in inches
                object@text_size * 72
            }
            return(object)
        }
    )

    # Source all the subclasses (else the methods will not be defined)
    source("src/utils/R_structs/text_sizes/plot_text_size.R")
    source("src/utils/R_structs/text_sizes/vectorized_text_size.R")
}
