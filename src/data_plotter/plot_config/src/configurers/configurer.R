options(error=function()traceback(2))
source("src/utils/util.R")
library(readr)
library(dplyr, warn.conflicts = FALSE)
library(magrittr)

#' @title Configurer
#' @description Configurer interface. All configurers
#' should inherit from this class. Configurers are
#' classes that perform configuration actions over
#' statistics data. Those will configure the data
#' plotted
setClass("Configurer",
    slots = list(
        # Arguments for the configurer
        csv_path = "character",
        # Data frame that contains the data
        df = "data.frame"
    )
)

#' Method that perform the configuration action
#' over the data
setGeneric(
  "perform",
  function(object) {
    standardGeneric("perform")
  }
)

#' Method that run the configurer
#' @param object The configurer to run
#' @return The object
setGeneric("run",
    function(object) {
    standardGeneric("run")
})

#' Method that write the data to a csv file
#' @param object The object to write
#' @param csv_path The path to write the data
#' @return The object
setGeneric(
    "write_data",
    function(object, csv_path) {
        standardGeneric("write_data")
    }
)

#' Method that parse the arguments for the configurer
#' from the command line
#' @param object The configurer object
#' @param args The arguments from the command line
#' @return A vector with the current arguments index
#' and the configurer object
setGeneric(
    "parse_args",
    function(.Object, args) {
        standardGeneric("parse_args")
    }
)

setValidity(
    "Configurer",
    function(object) {
        is_valid <- TRUE
        if (length(object@csv_path) == 0) {
            message("CSV path is empty")
        }
        if (length(object@df) == 0) {
            message("Data frame is empty")
        }
        is_valid
    }
)

setMethod(
    "write_data",
    "Configurer",
    function(object, csv_path) {
        write.table(object@df, csv_path, sep = " ", row.names = FALSE)
        object
    }
)

setMethod(
    "parse_args",
    "Configurer",
    function(.Object, args) {
        # Parse csv file path
        .Object@csv_path <- get_arg(args, 1)
        args %<>% shift(1)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "initialize",
    "Configurer",
    function(.Object, ..., args) {
        # Parse the arguments
        if (!missing(args)) {
            parse_result <- parse_args(.Object, args)
            # Ensure length of the vector is 2
            if (length(parse_result) != 2) {
                stop("Error parsing arguments. Unexpected return values while parsing")
            }
            # Ensure there is no arguments left
            if (length(parse_result$arguments) != 0) {
                stop("Error parsing arguments. There are arguments left")
            }
            .Object <- parse_result$configurer
            # Check if csv file exists
            if (!file.exists(.Object@csv_path)) {
                stop(paste0("File not found: ",
                    .Object@csv_path,
                    " Stopping..."))
            }
            # Read the csv file
            .Object@df <- read_data(.Object@csv_path)
            validObject(.Object)
        }
        # Return the object
        .Object
    }
)

setMethod(
    "run",
    "Configurer",
    function(object) {
        object <- perform(object)
        write_data(object, object@csv_path)
        object
    }
)