#!/usr/bin/Rscript
source("src/utils/util.R")
source("src/data_preprocessing/src/preprocessors/preprocessor.R")

setClass("Divider", contains = "Preprocessor",
    slots = list(
        # The operators (columns) to be used in the preprocessing
        src1_op = "character",
        src2_op = "character"
    ),
    prototype = list(
        src1_op = "",
        src2_op = ""
    )
) -> Divider

setValidity("Divider",
    function(object) {
        callNextMethod()
        is_valid <- TRUE
        if (object@src1_op == "" || object@src2_op == "") {
            message(paste(c("Divider must have exactly 2 operators!\n,",
                " DIV: Src1, Src2\n",
                "Operators: ", object@src1_op, object@src2_op), collapse = " "))
            is_valid <- FALSE
        }
        if (!object@src1_op %in% colnames(object@data) ||
            !object@src2_op %in% colnames(object@data)) {
            message(paste(c("Operators must be columns in the data frame!\n",
                "Operators: ", object@src1_op, object@src2_op), collapse = " "))
            is_valid <- FALSE
        }
        return(is_valid)
    }
)

setMethod("initialize",
    "Divider",
    function(.Object, src1_op = "", src2_op = "", ...) {
        .Object <- callNextMethod(.Object, ...)
        .Object@src1_op <- src1_op
        .Object@src2_op <- src2_op
        return(.Object)
    }
)

setMethod("preprocess",
    signature(object = "Divider"),
    function(object) {
        # Create the new column with the name of the first operator,
        # and the result of the division of the second operator 
        # by the third operator
        object@data[, object@destination_op] <-
            object@data[, object@src1_op] /
            object@data[, object@src2_op]
        return(object)
    }
)
arguments <- commandArgs(trailingOnly = TRUE)
csv_file <- get_arg(arguments, 1)
arguments <- shift(arguments, 1)
destination_op <- get_arg(arguments, 1)
arguments <- shift(arguments, 1)
src1_op <- get_arg(arguments, 1)
arguments <- shift(arguments, 1)
src2_op <- get_arg(arguments, 1)
arguments <- shift(arguments, 1)
if (length(arguments) > 0) {
    warning("Unused arguments left to parse!")
}

save_preprocessed_data(
    preprocess(
        Divider(csv_file = csv_file,
            destination_op = destination_op,
            src1_op = src1_op,
            src2_op = src2_op)))