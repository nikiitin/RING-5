#!/usr/bin/Rscript
library(patchwork)
library(magrittr)
library(ggplot2)
source("src/utils/util.R")

arguments <- commandArgs(trailingOnly = TRUE)
outputDir <- get_arg(arguments, 1)
arguments %<>% shift(1)
outputName <- get_arg(arguments, 1)
arguments %<>% shift(1)
n_plots_to_join <- get_arg(arguments, 1)
arguments %<>% shift(1)
plot_list <- list()
ids <- list()
sessionCachePath <- paste0(outputDir, "/", ".sessionCache/")
for (plot in 1:n_plots_to_join) {
    ids[[plot]] <- get_arg(arguments, 1)
    arguments %<>% shift(1)
}

for (id in ids) {
    data_path <- paste0(sessionCachePath, id, ".rds")
    print(paste0("Reading plot id:", id, "from: ", data_path))
    plot_list[[id]] <- readRDS(file = data_path)
}

if (length(plot_list) > 1) {
    pw <- plot_list[[1]]
    for (plot in plot_list[[2:length(plot_list)]]) {
        # Apply patchwork to join the plots
        pw <- pw + plot
    }
} else {
    pw <- plot_list[[1]]
}
ggsave(filename = paste0(outputDir, "/", outputName), plot = pw, width = 20, height = 20, units = "cm", dpi = 320)
