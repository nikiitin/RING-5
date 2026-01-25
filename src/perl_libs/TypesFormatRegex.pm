package TypesFormatRegex;
# Kind of "language" to parse gem5 stats files.
#
use strict;
use warnings;
use Exporter 'import';
our $VERSION = '1.00';
our @EXPORT  = qw(parseAndPrintLineWithFormat setFilterRegexes classifyLine);

# Imports from new modular packages
use Scanning::RegexUtils qw(:all);
use Scanning::Type::Configuration qw($confRegex);
use Scanning::Type::Scalar qw($scalarRegex);
use Scanning::Type::Distribution qw($distRegex $distEntry);
use Scanning::Type::Histogram qw($histogramRegex $histogramEntryRangeRegex);
use Scanning::Type::Vector qw($vectorRegex $vectorEntryRegex);
use Scanning::Type::Summary qw($summaryRegex);

# Note: Individual regexes are now imported.
# Methods below use them.

my $filtersRegexes;

sub getRealVariableNameFromLine {
    my ($line) = @_;
    $line =~ /($filtersRegexes)/;
    return $1;
}

sub getEntryNameFromLine {
    # Get the entry name from the line
    my ($line) = @_;
    # If is histogram it is a range
    if ($line =~ $histogramEntryRangeRegex) {
        $line =~ /($histogramEntryRangeRegex)/;
        return $1;
    }
    # If is distribution it is an integer or an
    # overflow/underflow
    if ($line =~ $distEntry) {
        $line =~ /($distEntry)/;
        return $1;
    }
    if ($line =~ $vectorEntryRegex &&
        $line !~ $summariesEntryRegex) {
        # Do not get summaries.
        # Vector format
        $line =~ /($vectorEntryRegex)/;
        return $1;
    }
    if ($line =~ $summariesEntryRegex) {
        $line =~ /($summariesEntryRegex)/;
        return $1;
    }
    # Do return empty string if no entry was found
    return "";
}

sub getValueFromLine {
    my ($line) = @_;
    # For configurations we will only use
    # value
    # Complex types won't use percentages
    # Values are always split by spaces or
    # equals (configurations)
    my @lineSplits = $line =~ $confRegex ?
        split /=/, $line :
        split /\s+/, $line;
    # Leave only values
    return $lineSplits[1];
}

sub removeCommentFromLine {
    my ($line) = @_;
    # Trim whitespaces before comment too    
    if ($line =~ /\s*$commentRegex/) {
        $line = $`;
    }
    return $line;
}

sub formatLine {
    my ($line) = @_;
    $line = removeCommentFromLine($line);
    # Get the real variable name
    my $varName = getRealVariableNameFromLine($line);
    # Comments are not used, remove
    my $entryName = getEntryNameFromLine($line);
    # Get the value that will be printed
    my $value = getValueFromLine($line);
    # Give the needed format for the line
    # Split the value with a slash
    return "$varName" . "$entryName" .  "/$value";
}

sub setFilterRegexes {
    my (@regexes) = @_;
    # Add all filters to same regex
    $filtersRegexes = join("|", @regexes);
    # Compile regexes
    $filtersRegexes = qr/$filtersRegexes/;
}

sub parseAndPrintLineWithFormat {
    my ($line) = @_;
    if ($line !~ $filtersRegexes) {
        return;
    }
    # Check if the line match any defined type
    # we have specified in this file.
    if ($line =~ $confRegex) {
        print "configuration/" . formatLine($line) . "\n";
    } elsif ($line =~ $scalarRegex) {
        print "scalar/" . formatLine($line) . "\n";
    } elsif ($line =~ $histogramRegex) {
        print "histogram/" . formatLine($line) . "\n";
    } elsif ($line =~ $distRegex) {
        print "distribution/" . formatLine($line) . "\n";
    } elsif ($line =~ $summaryRegex) {
        # Do not print summaries
        print "summary/" . formatLine($line) . "\n";
    } elsif ($line =~ $vectorRegex) {
        print "vector/" . formatLine($line) . "\n";
    } else {
        # Unknown data type found
        # DO NOT PRINT IT!
        # print "Unknown data type: $line\n";
    }
}

sub classifyLine {
    my ($line) = @_;
    
    # Check types in order with explicit captures
    
    # Configuration: name=value
    if ($line =~ /^($varNameRegex)=$confValueRegex$/) {
        return { type => 'configuration', name => $1, entry => undef };
    } 
    # Scalar: name value # comment
    elsif ($line =~ /^($varNameRegex)\s+$scalarValueRegex\s+$commentRegex?$/) {
        return { type => 'scalar', name => $1, entry => undef };
    } 
    # Histogram: name::range ...
    elsif ($line =~ /^($varNameRegex)($histogramEntryRangeRegex)\s+$complexValueRegex\s+$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://; 
        return { type => 'histogram', name => $name, entry => $entry }; 
    } 
    # Distribution: name::val ...
    elsif ($line =~ /^($varNameRegex)($distEntry)\s+$complexValueRegex\s+$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'distribution', name => $name, entry => $entry };
    } 
    # Summary: name::total ...
    elsif ($line =~ /^($varNameRegex)($summariesEntryRegex)\s+$scalarValueRegex\s+$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'summary', name => $name, entry => $entry };
    } 
    # Vector: name::entry ...
    elsif ($line =~ /^($varNameRegex)($vectorEntryRegex)\s+(?:$complexValueRegex|$scalarValueRegex)\s+$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'vector', name => $name, entry => $entry };
    }
    
    return undef;
}

1; # A module must end with a true value or "use" will report an error
