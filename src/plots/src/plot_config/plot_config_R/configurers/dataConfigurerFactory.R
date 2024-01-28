source("src/plots/src/plot_config/plot_config_R/configurers/dataFilter.R")
source("src/plots/src/plot_config/plot_config_R/configurers/dataMeanCalculator.R")
source("src/plots/src/plot_config/plot_config_R/configurers/normalize.R")
source("src/plots/src/plot_config/plot_config_R/configurers/ordering.R")
# Available configurators
configurators <- c("Filter", "Mean", "Normalize", "Sort")
get_configurer <- function(action, args) {
    action <- as.character(action)
    if (!action %in% configurators) {
        stop(paste("Unknown configurator:", action,
            "Available configurators:", paste(configurators, collapse = ", "),
            "At: ",
            traceback(),
            sep = "\n"))
    }
    action <- new(action, args = args)
    action
}