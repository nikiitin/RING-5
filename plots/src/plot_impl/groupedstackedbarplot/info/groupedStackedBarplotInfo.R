source("plots/src/plot_impl/stackedbarplot/info/stackedBarplotInfo.R")
# Define the S4 class for percentage stacked barplot
# NOTE: Same information as barplot
setClass("GroupedStackedBarplot_info", contains = "StackedBarplot_info")

# There is no need to extend the class, all information
# is already contained in the parent class

setMethod("check_data_info_correct",
  signature(object = "Barplot_info"),
  function(object) {
    # Checkings for gsbp are kinda different from sbp
    # Do not call parent method
    # Check that the z axis variables are in the data frame
    if (!all(object@conf_z %in% colnames(object@data))) {
      stop("The conf_z axis variables are not in the data frame.")
    }
    if (length(unique(object@data[, object@conf_z])) <= 1) {
        stop(paste0("Stacked barplots are not intended for only ",
            " one conf_z variable. Suggest to use barplot instead.",
            "conf_z is used as the entries of the grouped bars.",
            "Anyway, check the data for correctness."))
    }
    if (object@n_y <= 1) {
      stop(paste0("Stacked barplots are not intended for only ",
        " one y variable. Suggest to use simple (dodged) barplot",
        " instead."))
    }
    if (object@n_hidden_bars >= length(unique(object@data[, object@conf_z]))) {
      stop(paste0("The number of hidden bars must be lesser",
      " than the number of conf_z columns."))
    }
    object
  }
)