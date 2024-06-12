#!/bin/bash

# This script is a wrapper for the joiner binary. It is used to set the
# environment variables and to call the joiner binary.

# Set the environment variables
output_dir="/home/vnicolas/Workspace/repos/RING-5/valuepred-analysis-effective/plots"

output_name="joint_plot"
n_plots_to_join="2"
id1=("simTicks(grouped)microbenchmarks")
id2=("simTicks(grouped)STAMP") 

Rscript "/home/vnicolas/Workspace/repos/ringTest/RING-5/src/utils/joiner/src/joiner.R" "$output_dir" "$output_name" "$n_plots_to_join" "${id1[@]}" "${id2[@]}"