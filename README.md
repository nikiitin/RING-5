# RING-5
## TODO: add dependencies to pip: tqdm
R-based Implementation for aNalysis and Graphic generation on gem-5

## Preconditions
- Have GNU bash interpreter installed and running on Linux/Debian distribution. Bash tested release: 5.0.17(1)-release. Tested system: Ubuntu 20.04-LTS
- Have R statistical analysis tool installed. Tested version: 4.0.2
- Have Python3 installed. Tested version 3.8.10
## Building project
This tool relies on different technologies to build and keep track of dependencies needed to run. On first place, you should build the project, which in turn would download and install all dependencies. To give structure to the process, Unix Make tool is used, check [make](https://en.wikipedia.org/wiki/Make_(software)) in wikipedia. Makefile will make use of several more modernized and specialized dependency management tools.

WIP: explain how to build the project.

### Solving R dependencies
WIP: ask user if R should be installed (check version too) and install it.

#### Using renv for R package dependencies
WIP section
### Using pip for Python3 package dependencies
WIP section
