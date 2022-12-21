#!/bin/bash
parsed_data_file=$1
rm $parsed_data_file
shift 1

data_path=$1
shift 1


# Get all the stats we want to extract
nstats=$1
shift 1
stats=()
for i in $(seq 1 1 "$nstats")
do
    stats+=($1)
    shift 1
done

# Get all the configs we will classify experiments by
nconfs=$1
shift 1
configs=()
for i in $(seq 1 1 "$nconfs")
do
    configs+=($1)
    shift 1
done
configs+=("benchmark_name")
configs+=("random_seed")



# First introduce the header of the CSV
echo ${configs[@]} ${stats[@]} >> $parsed_data_file
# Do the parse
statsFiles=$(find "$data_path" -type f -name "stats.txt")
while read line; do  
    filePath=$line
    if [ ! -s "$filePath" ]
    then 
        echo "$filePath does not exist or is empty"
        continue
    fi
    comm="grep -E '"$(printf '%s|' "${configs[@]}|${stats[@]}" | sed 's/|$//')"' "$filePath""
    result=$(eval $comm)
    # Get the configuration of this simulation
    configStats=()
    for conf in ${configs[@]}; do
        statConf=$(echo "$result" | grep "$conf" | cut -d '=' -f 2 )
        if [ -z "$statConf" ]
        then    
            configStats+=("0")
        else
            configStats+=("$statConf")
        fi
    done
    # Extract all data from the file and do mean 
    # with all cpus found.
    data_csv=()
    for stat in ${stats[@]}; do
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