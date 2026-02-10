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
my @storedFilters;

sub getRealVariableNameFromLine {
    my ($line) = @_;

    # Optimization: Extract name part more efficiently
    # Use index() which is faster than regex for simple character search
    my $namePart = $line;
    my $sep_pos;

    # Find first separator: ::, space, or =
    if (($sep_pos = index($line, '::')) != -1) {
        $namePart = substr($line, 0, $sep_pos);
    }
    elsif (($sep_pos = index($line, ' ')) != -1) {
        $namePart = substr($line, 0, $sep_pos);
    }
    elsif (($sep_pos = index($line, '=')) != -1) {
        $namePart = substr($line, 0, $sep_pos);
    }

    # Optimization: Try exact match first (fastest path)
    foreach my $filter (@storedFilters) {
        return $filter if $namePart eq $filter;
    }

    # Then try anchored regex match
    foreach my $filter (@storedFilters) {
        return $filter if $namePart =~ /^$filter$/;
    }

    # Fallback for complex regexes
    foreach my $filter (@storedFilters) {
        return $filter if $namePart =~ /$filter/;
    }

    # Ultimate fallback
    return $1 if $line =~ /($filtersRegexes)/;
    return '';
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

    # Optimization: Use index() to detect separator type (faster than regex)
    my $sep_pos = index($line, '=');
    my @lineSplits;

    if ($sep_pos != -1) {
        # Configuration line (has =)
        @lineSplits = split /=/, $line, 2;  # Limit splits to 2 parts
    } else {
        # Complex type (space-separated)
        @lineSplits = split /\s+/, $line, 3;  # Limit splits to 3 parts (name, value, rest)
    }

    # Return value (second element)
    return defined($lineSplits[1]) ? $lineSplits[1] : '';
}

sub removeCommentFromLine {
    my ($line) = @_;
    # Optimization: Use index() to check for comment existence first
    my $comment_pos = index($line, '#');
    if ($comment_pos != -1) {
        $line = substr($line, 0, $comment_pos);
    }
    # Remove (Unspecified) if present
    $line =~ s/\(Unspecified\)\s*$//;
    # Trim trailing whitespace
    $line =~ s/\s+$//;
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
    @storedFilters = @regexes;
    # Add all filters to same regex
    $filtersRegexes = join("|", @regexes);
    # Compile regexes
    $filtersRegexes = qr/$filtersRegexes/;
}

sub parseAndPrintLineWithFormat {
    my ($line) = @_;

    # Early return optimization: check filter first
    return unless $line =~ $filtersRegexes;

    # Optimization: Check types in order of frequency (most common first)
    # and use elsif to avoid multiple regex matches

    # Scalar is most common - check first
    if ($line =~ $scalarRegex) {
        print "scalar/" . formatLine($line) . "\n";
    }
    # Vector is second most common
    elsif ($line =~ $vectorRegex) {
        print "vector/" . formatLine($line) . "\n";
    }
    # Distribution
    elsif ($line =~ $distRegex) {
        print "distribution/" . formatLine($line) . "\n";
    }
    # Histogram
    elsif ($line =~ $histogramRegex) {
        print "histogram/" . formatLine($line) . "\n";
    }
    # Summary
    elsif ($line =~ $summaryRegex) {
        print "summary/" . formatLine($line) . "\n";
    }
    # Configuration (least common)
    elsif ($line =~ $confRegex) {
        print "configuration/" . formatLine($line) . "\n";
    }
    # Unknown type - silently skip (optimization: no else block)
}

sub classifyLine {
    my ($line) = @_;

    # Check types in order with explicit captures

    # Configuration: name=value
    if ($line =~ /^($varNameRegex)=$confValueRegex$/) {
        return { type => 'configuration', name => $1, entry => undef };
    }
    # Scalar: name value # comment
    elsif ($line =~ /^($varNameRegex)\s+$scalarValueRegex$commentRegex?$/) {
        return { type => 'scalar', name => $1, entry => undef };
    }
    # Histogram: name::range ...
    elsif ($line =~ /^($varNameRegex)($histogramEntryRangeRegex)\s+$complexValueRegex$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'histogram', name => $name, entry => $entry };
    }
    # Distribution: name::val ...
    elsif ($line =~ /^($varNameRegex)($distEntry)\s+$complexValueRegex$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'distribution', name => $name, entry => $entry };
    }
    # Summary: name::total ...
    elsif ($line =~ /^($varNameRegex)($summariesEntryRegex)\s+$scalarValueRegex$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'summary', name => $name, entry => $entry };
    }
    # Vector: name::entry ...
    elsif ($line =~ /^($varNameRegex)($vectorEntryRegex)\s+(?:$complexValueRegex|$scalarValueRegex)$commentRegex?$/) {
        my $name = $1;
        my $entry = $2;
        $entry =~ s/^:://;
        return { type => 'vector', name => $name, entry => $entry };
    }

    return undef;
}

1; # A module must end with a true value or "use" will report an error
