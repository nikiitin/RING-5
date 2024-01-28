source("src/plots/src/plot_impl/stackedbarplot/info/stackedBarplotInfo.R")
# Define the S4 class for percentage stacked barplot
# NOTE: Same information as barplot
setClass("PercentageStackedBarplot_info", contains = "StackedBarplot_info")