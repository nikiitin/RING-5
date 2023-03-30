#!/bin/bash
# Do the parse
# Reduce charset for grep. Store
# the older one. Lang variable
# has usually the same value than rest
# of locals so I picked this one
LC_OLD="$LANG"
export LC_ALL=C
config_indexes=()
filePath=$1
shift 1
if [ ! -s "$filePath" ]
    then
        echo "$filePath does not exist or is empty"
        exit
fi
parsed_data_file=$1
shift 1
grep_pattern_length=$1
shift 1
grep_pattern=()
for ((i = 0; i < grep_pattern_length; i++)); do
    grep_pattern+=($1)
    shift 1
done
grep_configs=()
grep_configs_length=$1
shift 1
for ((i = 0; i < grep_configs_length; i++)); do
    grep_configs+=($1)
    shift 1
done
grep_stats=()
grep_stats_length=$1
shift 1
for ((i = 0; i < grep_stats_length; i++)); do
    grep_stats+=($1)
    shift 1
done

result=$(printf '%s\n' "${grep_pattern[@]}" | grep -E -f - "$filePath")

# Get the configuration of this simulation
configStats=()
for conf in ${grep_configs[@]}; do
    statConf=$(echo "$result" | grep "$conf" | cut -d '=' -f 2) 
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
# and do it on locked fashion, there are several instances of this
# script running at once
export LC_ALL="$LC_OLD"
exec 10>lock
# Tricky hack to lock on a file descriptor
# to handle multiple writes over the csv file
flock -x "10"     
echo "${configStats[@]} ${data_csv[@]}" >> $parsed_data_file 
exec 10>&-         

