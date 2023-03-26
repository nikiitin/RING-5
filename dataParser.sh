#!/bin/bash
parsed_data_file=$1
rm $parsed_data_file
shift 1

data_path=$1
shift 1


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
echo ${header_configs[@]} ${stat_header[@]} >> $parsed_data_file
# Do the parse
# Reduce charset for grep. Store
# the older one. Lang variable
# has usually the same value than rest
# of locals so I picked this one
LC_OLD="$LANG"
export LC_ALL=C
# Create configuration indexes variable
# This is commonly the same for all stats file
# so just calculate indexes and iterate over them
# (Avoid extra grep)
config_indexes=()
# Find stats name, usually standard name
statsFiles=$(find "$data_path" -type f -name "stats.txt")
while read line; do
    filePath=$line
    if [ ! -s "$filePath" ]
    then
        echo "$filePath does not exist or is empty"
        continue
    fi
    result=$(printf '%s\n' "${grep_pattern[@]}" | grep -F -f - "$filePath")

    # Get the configuration of this simulation
    configStats=()
    # Calculate the index array for config elements
    if [ ${#config_indexes[@]} -eq 0 ]; then
    	for conf in ${grep_configs[@]}; do
        	config_indexes+=($(echo "$result" | grep -n "$conf" | cut -f1 -d:))
    	done
    fi
    for conf_ind in ${config_indexes[@]}; do
    	statConf=$(echo "$result" | sed "$conf_ind!d" | cut -d '=' -f 2) 
        if [ -z "$statConf" ]
        then
         	configStats+=("0")
        else
           	configStats+=("$statConf")
        fi
    done

    # Extract all data from the file and do mean
    # with all cpus found.
    # This part is kinda dynamic but should be optimized!
    data_csv=()
    for ((stat_index = 0; stat_index < ${#grep_stats[@]}; stat_index++)); do
        stat=${grep_stats[stat_index]}

        cpusMean=0
        cpusRep=0
        while read -r data; do            
            # Parse the stat we are looking for
            parsedResult=$(echo $data |  tr -s ' ' | cut -d ' ' -f 2)
            # Calculate iteratively the mean between cpus
            cpusMean=$(echo "scale=6;$cpusMean+$parsedResult" | bc)
            cpusRep=$(($cpusRep + 1))
        done < <(echo "$result" | grep "$stat")
        if [ $cpusRep -gt 0 ]
        then
            cpusMean=$(echo "scale=8;$cpusMean/$cpusRep" | bc)
            data_csv+=($cpusMean)
        else
            data_csv+=(0)
        fi
    done
    # Put all stats from this simulation in only one line in csv
    echo ${configStats[@]} ${data_csv[@]} >> $parsed_data_file
done <<< $statsFiles
export LC_ALL="$LC_OLD"
