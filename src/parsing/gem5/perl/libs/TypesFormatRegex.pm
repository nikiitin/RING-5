package TypesFormatRegex;

use strict;
use warnings;
use Exporter 'import';
our $VERSION = '1.00';
our @EXPORT = qw(parseAndPrintLineWithFormat setFilterRegexes classifyLine resetLineContext finishLineContext printLineContext);

use Scanning::RegexUtils qw(:all);
use Scanning::Type::Configuration qw($confRegex);
use Scanning::Type::Scalar qw($scalarRegex);
use Scanning::Type::Distribution qw($distRegex);
use Scanning::Type::Histogram qw($histogramRegex);
use Scanning::Type::Vector qw($vectorRegex);

my $filtersRegexes;
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
    return $line =~ /^-+\s*Begin Simulation Statistics(?:\s*:\s*.*?)?\s*-+\s*$/;
}

sub _removeComment {
    my ($line) = @_;
    $line =~ s/\s*(?:#.*|\(Unspecified\))\s*$//;
    $line =~ s/\s+$//;
    return $line;
}

# Records retain source entry identity; scan_entry is its displayed bucket label.
sub _record {
    my ($type, $line) = @_;
    my ($identifier, $value) = split /\s+/, $line, 3;
    my ($name, $entry) = split /::/, $identifier, 2;
    return { type => $type, name => $name, entry => $entry,
             scan_entry => $entry, value => $value };
}

sub _rememberOnelineHistogramMetadata {
    my ($line) = @_;
    return 0 unless $line =~ /^($varNameRegex)::(bucket_size|min_bucket|max_bucket)\s+(-?\d+)$/;
    $onelineHistogramMetadata{$1}{$2} = int($3);
    push @pendingGeometry, _record('vector', $line);
    return 1;
}

# Geometry-looking vector entries remain data unless a histogram identifies them.
sub finishLineContext {
    my @entries = grep { !$identifiedHistograms{$_->{name}} } @pendingGeometry;
    @pendingGeometry = ();
    return \@entries;
}

sub _printRecords {
    my ($records) = @_;
    foreach my $record (@$records) {
        if ($record->{type} eq 'dump') {
            print "dump//\n";
            next;
        }
        # Summary fields use the worker protocol's ordinary entry representation.
        my $type = $record->{type} eq 'summary' ? 'vector' : $record->{type};
        my $identifier = $record->{name};
        $identifier .= "::$record->{entry}" if defined $record->{entry};
        print "$type/$identifier/$record->{value}\n";
    }
}

sub printLineContext {
    _printRecords(finishLineContext());
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
    return undef unless $line =~ /^($varNameRegex)::(-?\d+)\s+(?:$complexValueRegex|$scalarValueRegex)$/;
    my ($name, $entry) = ($1, $2);
    my $type = $entryTypeContext{$name};
    my $geometry = $onelineHistogramMetadata{$name};
    if (!defined $type && defined $geometry
        && exists $geometry->{bucket_size} && exists $geometry->{max_bucket}) {
        $type = 'histogram';
    }
    $type //= 'vector';
    my $record = _record($type, $line);
    if ($type eq 'histogram') {
        $identifiedHistograms{$name} = 1;
        $record->{scan_entry} = "$entry-$entry";
    }
    return $record;
}

sub _classifyOnelineHistogram {
    my ($line) = @_;
    return undef unless $line =~ /^($varNameRegex)\s+\|(.*)$/;
    my ($name, $payload) = ($1, $2);
    my $metadata = $onelineHistogramMetadata{$name};
    # Pipe-delimited vectors have no geometry and are not oneline histograms.
    return undef unless defined $metadata;
    die "Incomplete one-line histogram metadata for $name\n"
        unless exists $metadata->{bucket_size};

    my $bucket_size = $metadata->{bucket_size};
    # DistPrint sends geometry through ScalarPrint: nozero suppresses zero bounds.
    my $min_bucket = $metadata->{min_bucket} // 0;
    my $max_bucket = $metadata->{max_bucket} // 0;
    die "Invalid one-line histogram metadata for $name\n"
        unless $bucket_size > 0 && $max_bucket >= $min_bucket;

    my @groups = split /\s*\|\s*/, $payload;
    my @values;
    foreach my $group (@groups) {
        # gem5 omits percentages when the histogram's total is zero.
        die "Malformed one-line histogram bucket for $name: $group\n"
            unless $group =~ /^\s*(-?\d+)(?:\s+$floatRegex%\s+$floatRegex%)?\s*$/;
        push @values, $1;
    }
    my $expected = int(($max_bucket - $min_bucket) / $bucket_size) + 1;
    die "One-line histogram bucket count mismatch for $name: expected $expected, found "
        . scalar(@values) . "\n"
        unless scalar(@values) == $expected;

    my @records;
    for (my $index = 0; $index < @values; $index++) {
        my $start = $min_bucket + $index * $bucket_size;
        my $end = $start + $bucket_size - 1;
        $end = $max_bucket if $end > $max_bucket;
        my $entry = "$start-$end";
        push @records, { type => 'histogram', name => $name, entry => $entry,
                         scan_entry => $entry, value => $values[$index] };
    }
    $identifiedHistograms{$name} = 1;
    return \@records;
}

# One semantic classifier feeds both scanner aggregation and worker serialization.
# An empty list means a deferred metadata entry; undef means an unrecognized line.
sub classifyLine {
    my ($line) = @_;
    if (_beginStatsDump($line)) {
        my $records = finishLineContext();
        resetLineContext();
        push @$records, { type => 'dump' };
        return $records;
    }
    $line = _removeComment($line);
    return [] if _rememberOnelineHistogramMetadata($line);
    _rememberEntryTypeContext($line);
    my $point = _classifyNumericEntry($line);
    return [$point] if defined $point;
    my $oneline = _classifyOnelineHistogram($line);
    return $oneline if defined $oneline;

    if ($line =~ $confRegex) {
        my ($name, $value) = split /=/, $line, 2;
        return [{ type => 'configuration', name => $name, entry => undef,
                  scan_entry => undef, value => $value }];
    }
    if ($line =~ $scalarRegex) {
        return [_record('scalar', $line)];
    }
    if ($line =~ $histogramRegex) {
        my $record = _record('histogram', $line);
        $identifiedHistograms{$record->{name}} = 1;
        return [$record];
    }
    if ($line =~ $distRegex) {
        return [_record('distribution', $line)];
    }
    if ($line =~ /^$varNameRegex$summariesEntryRegex\s+$scalarValueRegex$/) {
        return [_record('summary', $line)];
    }
    if ($line =~ $vectorRegex) {
        return [_record('vector', $line)];
    }
    return undef;
}

sub setFilterRegexes {
    my (@regexes) = @_;
    die "Too many filter expressions" if scalar(@regexes) > 2048;
    foreach my $filter (@regexes) {
        die "Filter expression is too long" if length($filter) > 1024;
    }
    my $alternatives = join('|', map { "(?:$_)" } @regexes);
    $filtersRegexes = qr/^(?:$alternatives)(?=::|\s|=)/;
}

sub parseAndPrintLineWithFormat {
    my ($line) = @_;
    return unless _beginStatsDump($line) || $line =~ $filtersRegexes;
    my $records = classifyLine($line);
    if (defined $records) {
        _printRecords($records);
    } else {
        print STDERR "ERROR: unclassifiable line matched filter: $line\n";
    }
}

1;
