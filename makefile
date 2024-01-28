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

CHECK_R_VERSION_SCRIPT := "\
thisRVersion <- R.Version(); \
if(as.numeric(thisRVersion['major']) < 3){ \
	stop(paste0('R version should be at least 3.6.3 ', 'current is: ', thisRVersion['major'])); \
}; \
if(as.numeric(thisRVersion['major']) == 3 && as.numeric(thisRVersion['minor']) < 6){ \
	stop(paste0('R version should be at least 3.6.3 ', 'current is: ', thisRVersion['minor'])); \
}; \
"
# stop("R version should be at least 4.0.2"); \
# } \
# "

# if(as.numeric(thisRVersion$minor >= 0.2)){ \
# 	stop("R version should be at least 4.0.2"); \
# }"

# Check for all dependency management tools and install all
# dependencies for the project
build: check_python_dependencies check_R_dependencies generate_proj_file
	@echo "Build finished successfully"


#### OBJECTIVES FOR PERL ####
# Check if perl is installed
check_perl:
	@which perl > /dev/null || (echo "Perl is not installed. Please install perl >= 5.0.0 before proceeding."; exit 1)
# Check perl version is greater than 5.0.0
	@perl -e "use 5.0.0;"

#### OBJECTIVES FOR PYTHON ####
check_python_dependencies: check_python check_pip
	@echo "All python dependencies are solved"

check_python:
# Check if python is installed
	@which python3 > /dev/null || (echo "Python3 is not installed. Please install python >= 3.8 before proceeding."; exit 1)
# Check python version is greater than 3.8
	@python3 -c "import sys; assert sys.version_info >= (3,8), 'Python version should be greater than 3.8'"

check_pip: install_pip check_pip_dependencies
# Check if pip is installed
	@python3 -m pip > /dev/null || (echo "Could not manage to execute pip... aborting."; exit 1)

# Install pip
install_pip:
	@echo "Checking if pip is installed..."
	@python3 -m pip --version 2>/dev/null 1>/dev/null || (echo "pip is not installed. Installing..."; sudo apt install python3-pip; echo "pip correctly installed" || (echo "Could not install pip... aborting."; exit 1))
	@echo "pip could execute!"
# Check if pip dependencies are solved
check_pip_dependencies:
	@python3 -m pip install -r requirements.txt


#### OBJECTIVES FOR R ####
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

check_R:
# Check if R is installed. I think any R version should work... currently using 4.0.2
	@which R > /dev/null || (echo "R is not installed. Please install R before proceeding."; exit 1)
# Check R version is greater than 4.0.0
	@Rscript -e $(CHECK_R_VERSION_SCRIPT) || exit 1;

#### OBJECTIVES FOR PROJ CONFIG ####
generate_proj_file: init_proj_file add_project_path end_proj_file
	@echo "Project file generated successfully"

init_proj_file:
# Create proj file if it does not exist
# This is a file used to store project management information
	@touch .proj
# Add json start to proj file
	@echo "{" > .proj.json
# Let the rest of the objectives finish this file and add a closing bracket
# On to the final objective

add_project_path:
# Add project path to proj file
	@echo "Adding project path $(shell pwd) to proj file..."
# Create proj file if it does not exist
# This is a file used to store project management information
	@touch .proj
# Add project path to proj file
	@echo "	RingRoot:$(shell pwd)" >> .proj.json

end_proj_file:
# Add json end to proj file
	@echo "}" >> .proj.json