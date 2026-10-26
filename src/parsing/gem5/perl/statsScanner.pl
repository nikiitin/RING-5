#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/libs";
use Encode qw(decode FB_CROAK);
use TypesFormatRegex;

my $filename = shift or die "Usage: statsScanner.pl <stats_file>\n";
die "Usage: statsScanner.pl <stats_file>\n" if @ARGV;
open(my $fh, '<:raw', $filename) or die "Could not open statistics file: $!\n";
my $max_lines = $ENV{RING5_MAX_SCAN_LINES} // 1000000;
my $max_bytes = $ENV{RING5_MAX_SOURCE_BYTES} // 268435456;
die "Invalid scanner limit\n" unless $max_lines =~ /^\d+$/ && $max_lines > 0
    && $max_bytes =~ /^\d+$/ && $max_bytes > 0;
my (%variables, %rejected);
my ($line_count, $catalog_bytes) = (0, 0);
my $error_text = '';
resetLineContext();

sub reject_source {
    my ($name, $message) = @_;
    return if exists $rejected{$name};
    $rejected{$name} = 1;
    delete $variables{$name};
    $error_text .= "$name: $message; " if length($error_text) < 900;
    $error_text = substr($error_text, 0, 1000);
}

sub contracts {
    my ($evidence) = @_;
    return $evidence->{state} eq 'resolved' ? [$evidence->{kind}] : $evidence->{candidates};
}

sub process_records {
    my ($records) = @_;
    foreach my $record (@$records) {
        my $event = $record->{event};
        next unless $event eq 'source' || $event eq 'source_error';
        my $name = $record->{name};
        if ($event eq 'source_error') {
            reject_source($name, $record->{message});
            next;
        }
        next if exists $rejected{$name};
        if (!exists $variables{$name}) {
            $variables{$name} = { evidence => $record->{source_evidence}, entries => {} };
            $catalog_bytes += length(encodeRecord({ name => $name, type => undef,
                source_evidence => $record->{source_evidence}, entries => [],
                instances => [{source_name => $name, indices => []}] }));
        } else {
            my %allowed = map { $_ => 1 } @{contracts($variables{$name}{evidence})};
            my @intersection = grep { exists $allowed{$_} } @{contracts($record->{source_evidence})};
            if (!@intersection) {
                reject_source($name, 'Contradictory source contracts across observations');
                next;
            }
            $variables{$name}{evidence} = @intersection == 1
                ? {state => 'resolved', kind => $intersection[0], basis => 'wire_contract'}
                : {state => 'ambiguous', candidates => \@intersection};
        }
        foreach my $entry (@{$record->{entries}}) {
            next if exists $variables{$name}{entries}{$entry};
            $catalog_bytes += length(encodeRecord($entry)) + 1;
            die "Scanner catalog exceeds its byte limit\n" if $catalog_bytes > $max_bytes;
            $variables{$name}{entries}{$entry} = 1;
        }
        die "Scanner catalog exceeds its byte limit\n" if $catalog_bytes > $max_bytes;
    }
}

while (my $raw = <$fh>) {
    die "Scanner line limit exceeded\n" if ++$line_count > $max_lines;
    my $line = decode('UTF-8', $raw, FB_CROAK);
    $line =~ s/\r?\n\z//;
    my $records = classifyLine($line);
    process_records($records) if defined $records;
}
process_records(finishLineContext());
close($fh) or die "Could not close statistics file: $!\n";

my $written = 0;
sub write_part {
    my ($encoded) = @_;
    $written += length($encoded);
    die "Scanner output exceeds its byte limit\n" if $written > $max_bytes;
    print $encoded;
}
write_part('{"variables":[');
my $first = 1;
foreach my $name (sort keys %variables) {
    write_part(',') unless $first;
    $first = 0;
    my $data = $variables{$name};
    my $evidence = $data->{evidence};
    write_part(encodeRecord({ name => $name,
        type => $evidence->{state} eq 'resolved' ? $evidence->{kind} : undef,
        source_evidence => $evidence,
        entries => [sort keys %{$data->{entries}}],
        instances => [{source_name => $name, indices => []}] }));
}
write_part('],"error":' . encodeRecord($error_text eq '' ? undef : $error_text) . "}\n");
