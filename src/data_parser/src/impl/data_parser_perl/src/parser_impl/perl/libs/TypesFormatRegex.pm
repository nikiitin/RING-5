package TypesFormatRegex;
# Kind of "language" to parse gem5 stats files.
#
use strict;
use warnings;
use Exporter 'import';
our $VERSION = '1.00';
our @EXPORT  = qw(parseAndPrintLineWithFormat setFilterRegexes);

# Simple components regexes
my $floatRegex = qr/\d+\.\d+/;
my $varNameRegex = qr/[\d\.\w]+/;
my $confValueRegex = qr/[\d\.\w\-\/\(\)\,]+/;
my $scalarValueRegex = qr/\d+|$floatRegex/;
my $commentRegex = qr/#.*|\(Unspecified\)\s*/;


# Complex components regexes
#  Val perc   cumm. percent
# | 5  32.5%  63.4% |
my $complexValueRegex = qr/\d+\s+$floatRegex%\s+$floatRegex%/;
my $summariesEntryRegex = qr/::(samples|mean|gmean|stdev|total)/;

# Distribution components regexes
# | ::5
my $distEntryNumericRegex = qr/::\d+/;
my $distEntryOverflowRegex = qr/::overflows/;
my $distEntryUnderflowRegex = qr/::underflows/;
my $distEntry = qr/($distEntryNumericRegex|$distEntryOverflowRegex|$distEntryUnderflowRegex)/;

# Histogram component regexes
my $histogramEntryRangeRegex = qr/::\d+-\d+/;
# | ::1-5 |

# Vector components regexes
# Summaries already included in this regex (total)
# | ::Name | ::Total
my $vectorEntryRegex = qr/::[\w\.]+/;

# Formal types regexes
# | name=value |
my $confRegex = qr/^$varNameRegex=$confValueRegex$/;
# | name  value  comment |
my $scalarRegex = qr/^$varNameRegex?\s+$scalarValueRegex\s+$commentRegex?$/;
# | name::distEntryNumRegex  value  perc  cumm.percent  # Comment |
my $distRegex = qr/^$varNameRegex$distEntry\s+$complexValueRegex\s+$commentRegex?$/;
# | name::range1-range2  value  perc  cumm.percent  # Comment |
my $histogramRegex = qr/^$varNameRegex$histogramEntryRangeRegex\s+$complexValueRegex\s+$commentRegex?$/;
# | name::summVar  value  # Comment |
my $summaryRegex = qr/^$varNameRegex$summariesEntryRegex\s+$scalarValueRegex\s+$commentRegex?$/;
# | name::vectorEntryName  value  perc  cumm.percent  # Comment
my $vectorRegex = qr/^$varNameRegex$vectorEntryRegex\s+$complexValueRegex\s+$commentRegex?$/;

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
        print "Configuration/" . formatLine($line) . "\n";
    } elsif ($line =~ $scalarRegex) {
        print "Scalar/" . formatLine($line) . "\n";
    } elsif ($line =~ $histogramRegex) {
        print "Histogram/" . formatLine($line) . "\n";
    } elsif ($line =~ $distRegex) {
        print "Distribution/" . formatLine($line) . "\n";
    } elsif ($line =~ $summaryRegex) {
        # Do not print summaries
        return;
    } elsif ($line =~ $vectorRegex) {
        print "Vector/" . formatLine($line) . "\n";
    } else {
        # Unknown data type found
        # DO NOT PRINT IT!
        # print "Unknown data type: $line\n";
    }
}

1; # A module must end with a true value or "use" will report an error
