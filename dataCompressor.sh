#!/bin/bash
outFile=$1
rm $outFile
touch $outFile
shift 1

data_paths_length=$1
shift 1
data_paths=()
# Get all stats files path.
for i in $(seq 1 1 "$data_paths_length")
do
    data_paths+=($1)
    shift 1
done

nameToFind=$1
shift 1
finalDirName=$1
rm -r $finalDirName
mkdir $finalDirName
for i in $data_paths
do
    find "$i" -name "*stats.txt" -exec tar -rf "$outFile" {} \;
done
tar -xf "$outFile" -C "$finalDirName"
