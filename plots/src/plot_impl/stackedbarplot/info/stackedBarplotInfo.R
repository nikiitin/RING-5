source("plots/src/plot_impl/barplot/info/barplotInfo.R")
# Define the S4 class for stacked barplot
# NOTE: Same information as barplot
setClass("StackedBarplot_info",
    contains = "Barplot_info")