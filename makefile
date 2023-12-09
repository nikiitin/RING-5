# This makefile is used to solve all dependencies for the project
# Could not find better way to implement dependency management.

# Anyway, modern tools like renv for R and pip are used to track dependencies
# inside packages.

# In case renv is not installed, this makefile will install it and restore
# the dependencies for the project. Ensure R and renv are installed.

# Command to install renv
INSTALL_RENV_SCRIPT := "\
if (!('renv' %in% installed.packages())) { \
    message('renv is not installed. Installing...'); \
    install.packages('renv', repos = 'https://cloud.r-project.org'); \
    message('renv correctly installed'); \
} else { \
    message('renv is already installed'); \
}"

RESTORE_DEPENDENCIES_SCRIPT := "\
message('Restoring renv dependencies'); \
renv::restore(confirm = FALSE); \
message('Restored successfully'); \
"

# Check for all dependency management tools and install all
# dependencies for the project
build: check_R_dependencies
	@echo "Build finished successfully"

# Check dependencies for R and R packages
check_R_dependencies: check_R check_renv
	@echo "All R dependencies are solved"

#### OBJECTIVES FOR RENV ####
check_renv: install_renv check_renv_dependencies
# Check if renv was correctly installed after the objective install_renv
	@Rscript -e "find.package('renv')" 2>/dev/null 1>/dev/null || (echo "renv could not be installed correctly... Exiting."; exit 1)


# Install renv package: dependency manager for R
install_renv:
# renv is the depenedency manager for R. It is used to track R packages and versions
# It is used to track R packages and versions
# Check if renv is installed, else, ask if user wants to install it
	@if [ ! -f renv.lock ]; then \
        echo "renv is not initialized. renv.lock Should be cloned from repository... Exiting."; \
        exit 1; \
    fi
	@echo "Checking if renv is installed..."
	@Rscript -e $(INSTALL_RENV_SCRIPT)

check_renv_dependencies:
# Check if renv is active. If not, activate it
	@Rscript -e "renv::activate()"
# Check if renv dependencies are solved. If not, restore them
	@Rscript -e $(RESTORE_DEPENDENCIES_SCRIPT)
	@Rscript -e "renv::deactivate()"

#### OBJECTIVES FOR R ####
check_R:
# Check if R is installed. I think any R version should work... currently using 4.0.2
	@which R > /dev/null || (echo "R is not installed. Please install R before proceeding."; exit 1)