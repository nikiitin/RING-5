source("src/plots/src/plot_impl/stackedbarplot/info/stackedBarplotInfo.R")
# Define the S4 class for percentage stacked barplot
# NOTE: Same information as barplot
setClass("PercentageStackedBarplot_info", contains = "StackedBarplot_info")

setMethod("check_data_info_correct",
  signature(object = "StackedBarplot_info"),
  function(object) {
    object
  }
)