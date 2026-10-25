package TypesFormatRegex;
# Kind of "language" to parse gem5 stats files.
#
use strict;
use warnings;
use Exporter 'import';
our $VERSION = '1.00';
our @EXPORT  = qw(parseAndPrintLineWithFormat setFilterRegexes classifyLine resetLineContext finishLineContext printLineContext);

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
my %onelineHistogramMetadata;
my %entryTypeContext;
my @pendingGeometry;
my %identifiedHistograms;

sub resetLineContext {
    %onelineHistogramMetadata = ();
    %entryTypeContext = ();
    @pendingGeometry = ();
    %identifiedHistograms = ();
}

sub _beginStatsDump {
    my ($line) = @_;
    return 0 unless $line =~ /^-+\s*Begin Simulation Statistics(?:\s*:\s*.*?)?\s*-+\s*$/;
    return 1;
}

sub _rememberOnelineHistogramMetadata {
    my ($line) = @_;
    if ($line =~ /^($varNameRegex)::(bucket_size|min_bucket|max_bucket)\s+(-?\d+)$commentRegex$/) {
        $onelineHistogramMetadata{$1}{$2} = int($3);
        push @pendingGeometry, { type => 'vector', name => $1, entry => $2, value => $3 };
        return 1;
    }
    return 0;
}

# Geometry-looking vector entries remain data unless a histogram identifies them.
sub finishLineContext {
    my @entries = grep { !$identifiedHistograms{$_->{name}} } @pendingGeometry;
    @pendingGeometry = ();
    return \@entries;
}

sub printLineContext {
    foreach my $entry (@{finishLineContext()}) {
        print "vector/$entry->{name}::$entry->{entry}/$entry->{value}\n";
    }
}

sub _rememberEntryTypeContext {
    my ($line) = @_;
    return unless $line =~ /^($varNameRegex)::(gmean|samples|mean|stdev|underflows|overflows)\s+/;
    my ($name, $entry) = ($1, $2);
    if ($entry eq 'gmean') {
        # gem5 DistPrint emits this reserved summary only for Hist storage.
        $entryTypeContext{$name} = 'histogram';
    } elsif ($entry eq 'underflows' || $entry eq 'overflows') {
        $entryTypeContext{$name} = 'distribution';
    } elsif (!exists $entryTypeContext{$name}) {
        $entryTypeContext{$name} = 'distribution';
    }
}

sub _classifyNumericEntry {
    my ($line) = @_;
    return undef unless $line =~ /^($varNameRegex)::(-?\d+)\s+(?:$complexValueRegex|$scalarValueRegex)$commentRegex$/;
    my ($name, $entry) = ($1, $2);
    my $type = $entryTypeContext{$name};
    my $geometry = $onelineHistogramMetadata{$name};
    if (!defined $type && defined $geometry
        && exists $geometry->{bucket_size} && exists $geometry->{max_bucket}) {
        $type = 'histogram';
    }
    # Numeric vector entries have no distribution summaries or boundaries.
    $type //= 'vector';
    $identifiedHistograms{$name} = 1 if $type eq 'histogram';
    return { type => $type, name => $name, entry => $entry,
             value => getValueFromLine(removeCommentFromLine($line)) };
}

sub _classifyOnelineHistogram {
    my ($line) = @_;
    my $clean = removeCommentFromLine($line);
    return undef unless $clean =~ /^($varNameRegex)\s+\|(.*)$/;

    my $name = $1;
    my $payload = $2;
    my $metadata = $onelineHistogramMetadata{$name};
    return undef unless defined $metadata;
    die "Incomplete one-line histogram metadata for $name\n"
        unless exists $metadata->{bucket_size} && exists $metadata->{max_bucket};

    $identifiedHistograms{$name} = 1;
    my $bucket_size = $metadata->{bucket_size};
    my $max_bucket = $metadata->{max_bucket};
    # Older fixtures omit min_bucket and describe histograms starting at zero.
    my $min_bucket = $metadata->{min_bucket} // 0;
    die "Invalid one-line histogram metadata for $name\n"
        unless $bucket_size > 0 && $max_bucket >= $min_bucket;

    my @groups = split /\s*\|\s*/, $payload;
    my @values;
    foreach my $group (@groups) {
        die "Malformed one-line histogram bucket for $name: $group\n"
            unless $group =~ /^\s*(-?\d+)\s+$floatRegex%\s+$floatRegex%\s*$/;
        push @values, $1;
    }

    my $expected = int(($max_bucket - $min_bucket) / $bucket_size) + 1;
    die "One-line histogram bucket count mismatch for $name: expected $expected, found "
        . scalar(@values) . "\n"
        unless scalar(@values) == $expected;

    my @entries;
    for (my $index = 0; $index < @values; $index++) {
        my $start = $min_bucket + $index * $bucket_size;
        my $end = $start + $bucket_size - 1;
        $end = $max_bucket if $end > $max_bucket;
        push @entries, { entry => "$start-$end", value => $values[$index] };
    }
    return { type => 'histogram', name => $name, entries => \@entries };
}

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
        return $namePart if $namePart eq $filter;
    }

    # Then try anchored regex match
    foreach my $filter (@storedFilters) {
        return $namePart if $namePart =~ /^(?:$filter)$/;
    }

    # parseAndPrintLineWithFormat already performed the same anchored filter
    # check, so a non-match here is malformed rather than a reason to search
    # arbitrary text later in the line.
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
    die "Too many filter expressions" if scalar(@regexes) > 2048;
    foreach my $filter (@regexes) {
        die "Filter expression is too long" if length($filter) > 1024;
    }
    @storedFilters = @regexes;
    # Add all filters to same regex
    $filtersRegexes = join("|", map { "(?:$_)" } @regexes);
    # Compile regexes
    $filtersRegexes = qr/^(?:$filtersRegexes)(?=::|\s|=)/;
}

sub parseAndPrintLineWithFormat {
    my ($line) = @_;

    # Dump boundaries preserve temporal observations when bucket geometry changes.
    if (_beginStatsDump($line)) {
        printLineContext();
        resetLineContext();
        print "dump//\n";
        return;
    }

    # Early return optimization: check filter first
    return unless $line =~ $filtersRegexes;

    # Gem5's Stats::oneline histogram format writes its bucket geometry on
    # preceding metadata lines, followed by one pipe-delimited row.  Consume
    # the metadata rather than exposing it as fake vector buckets.
    return if _rememberOnelineHistogramMetadata($line);
    _rememberEntryTypeContext($line);
    my $point = _classifyNumericEntry($line);
    if (defined $point) {
        print "$point->{type}/$point->{name}::$point->{entry}/$point->{value}\n";
        return;
    }
    my $oneline = _classifyOnelineHistogram($line);
    if (defined $oneline) {
        foreach my $item (@{$oneline->{entries}}) {
            print "histogram/$oneline->{name}::$item->{entry}/$item->{value}\n";
        }
        return;
    }

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
    # Histogram
    elsif ($line =~ $histogramRegex) {
        print "histogram/" . formatLine($line) . "\n";
    }
    # Distribution
    elsif ($line =~ $distRegex) {
        print "distribution/" . formatLine($line) . "\n";
    }
    # Summary
    elsif ($line =~ $summaryRegex) {
        print "summary/" . formatLine($line) . "\n";
    }
    # Configuration (least common)
    elsif ($line =~ $confRegex) {
        print "configuration/" . formatLine($line) . "\n";
    }
    # A line that matched the user's filter but no type regex is a requested
    # stat we could not classify: report it (the Python stderr-drainer surfaces
    # "ERROR" lines as warnings) so missingness is traceable, never silent.
    else {
        print STDERR "ERROR: unclassifiable line matched filter: $line\n";
    }
}

sub classifyLine {
    my ($line) = @_;
    if (_beginStatsDump($line)) {
        my $pending = finishLineContext();
        resetLineContext();
        return @$pending ? { type => 'pending_entries', entries => $pending } : undef;
    }

    if (_rememberOnelineHistogramMetadata($line)) {
        return { type => 'oneline_metadata', name => undef, entry => undef };
    }
    _rememberEntryTypeContext($line);
    my $point = _classifyNumericEntry($line);
    if (defined $point) {
        # Scan labels describe geometry; parser keys retain source entry identity
        # so explicit vector/distribution reinterpretations remain possible.
        $point->{entry} = "$point->{entry}-$point->{entry}"
            if $point->{type} eq 'histogram';
        return $point;
    }
    my $oneline = _classifyOnelineHistogram($line);
    return $oneline if defined $oneline;

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
