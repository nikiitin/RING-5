#!/usr/bin/Rscript
library(readr)

# Define the preprocessor class
setClass("Preprocessor",
    slots = list(
        # Data frame to be preprocessed
        csv_file = "character",
        data = "data.frame",
        destination_op = "character"
    ),
    prototype = list(
        csv_file = "",
        data = data.frame(),
        destination_op = ""
)) -> Preprocessor

# Define the initialize method for the Preprocessor class
setMethod("initialize",
    "Preprocessor",
    function(.Object, csv_file = "", destination_op = "", ...) {
        .Object <- callNextMethod(.Object, ...)
        .Object@csv_file <- csv_file
        .Object@data <- read.table(csv_file, sep = " ", header = TRUE)
        .Object@destination_op <- destination_op
        return(.Object)
    }
)

# Define the validity method for the Preprocessor class
setValidity("Preprocessor",
    function(object) {
        is_valid <- TRUE
        if (object@csv_file == "") {
            message("CSV file must be set!")
            is_valid <- FALSE
        }
        if (!file.exists(object@csv_file)) {
            message(paste(c("CSV file does not exist!",
                "CSV file: ", object@csv_file), collapse = " "))
            is_valid <- FALSE
        }
        if (object@destination_op == "") {
            message(paste(c("Destination operator must be set!",
                "Destination operator: ", object@destination_op),
                collapse = " "))
            is_valid <- FALSE
        }
        if (!object@destination_op %in% colnames(object@data)) {
            message(paste(c("Destination operator must be",
                "a column in the data frame!",
                "Destination operator: ", object@destination_op),
                collapse = " "))
            is_valid <- FALSE
        }
        if (object@data == data.frame()) {
            paste(c("Data must be set!", collapse = " "))
            is_valid <- FALSE
        }
        return(is_valid)
    }
)

setGeneric("preprocess", function(object) {
    standardGeneric("preprocess")
})

setGeneric("save_preprocessed_data", function(object) {
    standardGeneric("save_preprocessed_data")
})

setMethod("save_preprocessed_data",
    "Preprocessor",
    function(object) {
        write.table(object@data, file = object@csv_file,
            sep = " ", row.names = FALSE)
    }
)