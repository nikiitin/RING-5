package TypesFormatRegex;

use strict;
use warnings;
use Exporter 'import';
use JSON::PP;
use Scanning::RegexUtils qw($scalarValueRegex $floatRegex $varNameRegex);

our @EXPORT = qw(classifyLine finishLineContext resetLineContext setFilterRegexes parseAndPrintLineWithFormat printLineContext encodeRecord);
my $json = JSON::PP->new->canonical(1)->utf8(1);
my $filtersRegexes;
my %sources;
my $context_bytes = 0;
my $wire_bytes = 0;
my $max_bytes = $ENV{RING5_MAX_SOURCE_BYTES} // 268435456;
my $max_cell = 4194304;
die "Invalid source decoder byte limit\n" unless $max_bytes =~ /^\d+$/ && $max_bytes > 0;

sub encodeRecord {
    return $json->encode($_[0]);
}

sub resetLineContext {
    %sources = ();
    $context_bytes = 0;
    $wire_bytes = 0;
}

sub _charge {
    my ($text) = @_;
    die "Source decoder text exceeds its byte limit\n" if length($text) > $max_bytes;
    $context_bytes += length(encodeRecord($text)) + 64;
    die "Source decoder context exceeds its byte limit\n" if $context_bytes > $max_bytes;
}

sub _source {
    my ($name) = @_;
    die "Source name exceeds the matching limit\n" if length($name) > 1024;
    if (!exists $sources{$name}) {
        _charge($name);
        $sources{$name} = { shapes => {}, entries => {}, geometry => {} };
    }
    return $sources{$name};
}

sub _error {
    my ($name, $message) = @_;
    my $source = _source($name);
    $source->{error} //= substr($message, 0, 1000);
    return [];
}

sub _measurement {
    my ($name, $shape, $entry, $value) = @_;
    die "Source cell exceeds the character limit\n" if length($value) > $max_cell;
    my $source = _source($name);
    $source->{shapes}{$shape} = 1;
    if (defined $entry && !exists $source->{entries}{$entry}) {
        die "Source entry exceeds the matching limit\n" if length($entry) > 1024;
        _charge($entry);
        $source->{entries}{$entry} = 1;
    }
    if (defined $entry && $entry =~ /^(?:bucket_size|min_bucket|max_bucket)$/) {
        if (!exists $source->{geometry}{$entry} || $source->{geometry}{$entry} ne $value) {
            if (exists $source->{geometry}{$entry}) {
                $context_bytes -= length(encodeRecord($source->{geometry}{$entry})) + 64;
            }
            _charge($value);
            $source->{geometry}{$entry} = $value;
        }
    }
    return [{ event => 'measurement', name => $name, shape => $shape,
              entry => $entry, value => $value }];
}

# Candidates name supported decoder contracts, never hidden C++ producer classes.
sub _candidates {
    my ($source) = @_;
    my @shapes = keys %{$source->{shapes}};
    return undef if @shapes != 1;
    return ['scalar'] if $shapes[0] eq 'scalar';
    return ['configuration'] if $shapes[0] eq 'configuration';
    my @entries = keys %{$source->{entries}};
    my ($distribution, $histogram, $hist_context) = (1, 1, 0);
    my $geometry = $source->{geometry};
    if (exists $geometry->{bucket_size} && exists $geometry->{min_bucket}
        && exists $geometry->{max_bucket}
        && $geometry->{bucket_size} =~ /^\d+$/ && $geometry->{bucket_size} > 0
        && $geometry->{min_bucket} =~ /^-?\d+$/ && $geometry->{max_bucket} =~ /^-?\d+$/
        && $geometry->{min_bucket} <= $geometry->{max_bucket}) {
        $hist_context = 1;
    }
    foreach my $entry (@entries) {
        next if $entry =~ /^(?:bucket_size|min_bucket|max_bucket)$/;
        next if $entry =~ /^(?:samples|mean|stdev|total)$/;
        if ($entry eq 'gmean') {
            $distribution = 0;
            $hist_context = 1;
        } elsif ($entry =~ /^(?:underflows|overflows|min_value|max_value)$/) {
            $histogram = 0;
        } elsif ($entry =~ /^-?\d+--?\d+$/) {
            $hist_context = 1;
        } elsif ($entry =~ /^$floatRegex(?:-$floatRegex)?$/) {
            $histogram = 0 unless $entry =~ /^-?\d+$/;
        } else {
            $distribution = 0;
            $histogram = 0;
        }
    }
    $histogram = 0 unless $hist_context;
    my @candidates = ('vector');
    push @candidates, 'distribution' if $distribution;
    push @candidates, 'histogram' if $histogram;
    return [sort @candidates];
}

sub finishLineContext {
    my @records;
    foreach my $name (sort keys %sources) {
        my $source = $sources{$name};
        my $candidates = _candidates($source);
        if (defined $source->{error} || !defined $candidates) {
            push @records, { event => 'source_error', name => $name,
                message => $source->{error} // 'Contradictory scalar, text or entry source observations' };
            next;
        }
        my $evidence = @$candidates == 1
            ? { state => 'resolved', kind => $candidates->[0], basis => 'wire_contract' }
            : { state => 'ambiguous', candidates => $candidates };
        push @records, { event => 'source', name => $name,
            source_evidence => $evidence, entries => [sort keys %{$source->{entries}}] };
    }
    %sources = ();
    $context_bytes = 0;
    return \@records;
}

sub classifyLine {
    my ($line) = @_;
    if ($line =~ /^-+\s*(?:Begin|End) Simulation Statistics(?:\s*:\s*.*?)?\s*-+\s*$/) {
        my $records = finishLineContext();
        push @$records, { event => 'dump' };
        return $records;
    }
    return [] if $line =~ /^\s*(?:#.*)?$/;
    if ($line =~ /^($varNameRegex)=(.*)$/) {
        return _measurement($1, 'configuration', undef, $2);
    }
    $line =~ s/\s*#.*$//;
    $line =~ s/\s+\([^\r\n]*\)\s*$//;
    $line =~ s/\s+$//;
    if ($line =~ /^($varNameRegex)\s+\|(.*)$/) {
        my ($name, $payload) = ($1, $2);
        my @values;
        foreach my $part (split /\|/, $payload, -1) {
            return _error($name, 'Malformed oneline numeric cell')
                unless $part =~ /^\s*($scalarValueRegex)(?:\s+$scalarValueRegex%){0,2}\s*$/;
            push @values, $1;
        }
        my $source = _source($name);
        $source->{shapes}{entry} = 1;
        return [{ event => 'measurement', name => $name, shape => 'oneline', values => \@values,
                  reported_geometry => {%{$source->{geometry}}} }];
    }
    if ($line =~ /^($varNameRegex)::(\S+)\s+($scalarValueRegex)(?:\s+$scalarValueRegex%){0,2}$/) {
        return _measurement($1, 'entry', $2, $3);
    }
    if ($line =~ /^($varNameRegex)\s+($scalarValueRegex)(?:\s+$scalarValueRegex%){0,2}$/) {
        return _measurement($1, 'scalar', undef, $2);
    }
    if ($line =~ /^($varNameRegex)(?=::|\s|=)/) {
        return _error($1, 'Malformed source measurement');
    }
    return undef;
}

sub setFilterRegexes {
    my (@regexes) = @_;
    die "Too many filter expressions\n" if @regexes > 2048;
    die "Filter expression is too long\n" if grep { length($_) > 1024 } @regexes;
    my $alternatives = join('|', map { "(?:$_)" } @regexes);
    $filtersRegexes = qr/^(?:$alternatives)(?=::|\s|=)/;
}

sub _printRecords {
    my ($records) = @_;
    foreach my $record (@$records) {
        my $encoded = encodeRecord($record) . "\n";
        $wire_bytes += length($encoded);
        die "Source decoder output exceeds its byte limit\n" if $wire_bytes > $max_bytes;
        print $encoded;
    }
}

sub printLineContext {
    _printRecords(finishLineContext());
}

sub parseAndPrintLineWithFormat {
    my ($line) = @_;
    return unless $line =~ /^-+\s*(?:Begin|End) Simulation Statistics/
        || $line =~ $filtersRegexes;
    my $records = classifyLine($line);
    _printRecords($records) if defined $records;
}

1;
