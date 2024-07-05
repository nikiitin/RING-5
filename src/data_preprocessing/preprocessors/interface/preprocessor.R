#!/usr/bin/Rscript

library(readr)
library(methods)
source("src/utils/util.R")

# Define the preprocessor class
setClass("Preprocessor",
    slots = list(
        # Data frame to be preprocessed
        data = "data.frame",
        # The operators (columns) to be used in the preprocessing
        operators = "vector"
    )
)

# Define the initialize method for the Preprocessor class
setMethod("initialize",
    "Preprocessor",
    function(.Object, data, operators) {
        .Object@data <- data
        .Object@operators <- operators
        .Object
    }
)

# Define the validity method for the Preprocessor class
setValidity("Preprocessor",
    function(object) {
        if (!all(object@operators %in% colnames(object@data))) {
            paste(c("Operators must be columns in the data frame!", 
                    "Operators: ", object@operators), collapse = " ")
        }
        TRUE
    }
)

setGeneric("preprocess", function(object) {
    standardGeneric("preprocess")
})
source("src/data_preprocessing/preprocessors/src/Divider.R")

arguments <- commandArgs(trailingOnly = TRUE)
stats_file <- get_arg(arguments, 1)
arguments <- shift(arguments, 1)
data <- read.table(stats_file, sep = " ", header = TRUE)

# How many preprocessings will be done
n_preprocessings <- as.numeric(get_arg(arguments, 1))
arguments <- shift(arguments, 1)

for (i in 1:n_preprocessings) {
    # What operation will be performed?
    process_type <- get_arg(arguments, 1)
    arguments <- shift(arguments, 1)
    # How many operators will be used in the preprocessing
    n_operators <- as.numeric(get_arg(arguments, 1))
    arguments <- shift(arguments, 1)
    # Operators to be used in the preprocessing
    operators <- get_arg(arguments, n_operators)
    arguments <- shift(arguments, n_operators)
    # Create the preprocessor object
    preprocessor <- new(process_type,
        data = data, 
        operators = operators)
    # Preprocess the data
    data <- preprocess(preprocessor)
}

write.table(data, file = stats_file, sep = " ", row.names = FALSE)