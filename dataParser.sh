#!/bin/bash
parsed_data_file=$1
rm $parsed_data_file
shift 1
data_n_files=$1
data_paths=()
shift 1
for i in $(seq 1 1 "$data_n_files")
do
    data_paths+=$1
    shift 1
done

# Get all the stats we want to extract
nstats=$1
shift 1
grep_stats=()
header_stat=()

for i in $(seq 1 1 "$nstats")
do
    IFS="/" # Set IFS here as we do not want to remove whitespaces
    stat="$1"
    stat_header="$stat"
    # Avoid regexp on grep expressions
    if [[ "$stat" == *".whitespace" ]]
    then
        # Add endline character for header
        stat_header="${stat/\.whitespace/\.f}"
        stat="${stat/\.whitespace/ }"
    fi
    grep_stats+=($stat)
    header_stat+=($stat_header)
    unset IFS
    shift 1
done

# Get all the configs we will classify experiments by
nconfs=$1
shift 1
grep_configs=()
header_configs=()
for i in $(seq 1 1 "$nconfs")
do
    IFS="/"
    conf="$1"
    conf_header="$conf"
    # Avoid regexp on grep expressions
    if [[ "$conf" == *".whitespace" ]]
    then
        # Add endline character for header
	    conf_header="${conf/\.whitespace/\.f}"
        conf="${stat/\.whitespace/ }"
    fi
    grep_configs+=($conf)
    header_configs+=($conf_header)
    unset IFS
    shift 1
done
header_configs+=("benchmark_name")
grep_configs+=("benchmark_name")
header_configs+=("random_seed")
grep_configs+=("random_seed")

grep_pattern=("${grep_configs[@]}" "${grep_stats[@]}")

# In parser config take in count that
# .f ending will be added to not trimmed
# stats and config names

# First introduce the header of the CSV
echo ${header_configs[@]} ${header_stat[@]} >> $parsed_data_file

# Create configuration indexes variable
# This is commonly the same for all stats file
# so just calculate indexes and iterate over them
# (Avoid extra grep)
config_indexes=()
# Find stats name, usually standard name
statsFiles=()
for path in $data_paths
do
    echo "Adding $path files"
    # Multifile parsing
    statsFiles+=$(find "$path" -type f -name "stats.txt")
done

while read line; do
    # In my system maximum arguments are >2000000
    # I hope you won't use that MANY arguments
    ./meanCalculatorCpu.sh "$line" "$parsed_data_file" "${#grep_pattern[@]}" "${grep_pattern[@]}" "${#grep_configs[@]}" "${grep_configs[@]}" "${#grep_stats[@]}" "${grep_stats[@]}" &
    # Let's run in parallel! 
done <<< $statsFiles
echo "Waiting for stats files parsing"
wait
# Once finished remove lock file
rm lock
echo "Finished parsing"

