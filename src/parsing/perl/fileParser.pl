#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/../../perl_libs";
# Include TypeFormatRegex which will provide
# a strong data type syntax and can format
# the output to match needed syntax
use TypesFormatRegex;

# Stat file being parsed
my $filename = shift or die "Please provide a filename as an argument.\n";
# At least provide one filter
die "Please provide at least one filter as an argument.\n" unless @ARGV;
# Filters for variable names
setFilterRegexes(@ARGV);
# Open the statistics file
open(my $fh, '<', $filename) or die "Could not open file '$filename' $!";

# Parse every line, chomping the \n and printing
# the line with the needed format.
# @see TypesFormatRegex
while (my $line = <$fh>) {
    chomp $line;
    # Parse and print line with format
    parseAndPrintLineWithFormat($line);
}
# Remember to close the filehandler
close($fh);
