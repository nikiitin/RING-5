source("renv/activate.R")
renv_path <- "renv/activate.R"
proj_file_path <- ".proj.json"
ring_env <- new.env()
if (file.exists(renv_path)) {
    source(renv_path)
} else {
    stop(paste("renv files not found. Please, run renv::activate()",
        "to create the renv files",
        "Additionally, please run renv::restore() to restore the environment",
        sep = "\n"))
}
if (file.exists(proj_file_path)) {
    # Get the json from proj_file_path
    ring_env$proj_json <- jsonlite::read_json(proj_file_path)
    if ("RingRoot" %in% names(ring_env$proj_json)) {
        ring_env$root_dir <- ring_env$proj_json$RingRoot
    } else {
        stop(paste("RingRoot not found in the project file.",
            "Stopping...",
            sep = "\n"))
    }
} else {
   stop(paste("Project file not found. It seems the project was not built.",
       "Please, run make build to build the project.",
       sep = "\n"))
}
# Set the working directory to the main repo directory
setwd(ring_env$root_dir)
