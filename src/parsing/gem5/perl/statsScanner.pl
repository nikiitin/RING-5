#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/libs";
use TypesFormatRegex;

my $filename = shift or die "Usage: statsScanner.pl <stats_file>\n";
die "Usage: statsScanner.pl <stats_file>\n" if @ARGV;

open(my $fh, '<', $filename) or die "Could not open file '$filename' $!";

# Data structure to hold discovered variables
# { name => { type => type, entries => [entries...] } }
my %discovered_vars;
my $line_count = 0;
my $max_lines = $ENV{RING5_MAX_SCAN_LINES} // 1_000_000;
die "Invalid scanner line limit\n" unless $max_lines =~ /^\d+$/ && $max_lines > 0;

TypesFormatRegex::resetLineContext();



# Helper subroutines

sub processSummary {
    my ($name, $entry, $vars) = @_;

    # Check if variable already exists
    if (exists $vars->{$name}) {
         addEntry($name, $entry, $vars);

         if ($vars->{$name}{type} eq 'scalar') {
             $vars->{$name}{type} = 'vector';
         }
         # Upgrade Vector to Distribution if summary implies advanced stats
         # BUT: Do NOT downgrade Histogram to Distribution!
         # Histograms with summary stats remain Histograms
         if ($vars->{$name}{type} eq 'vector' &&
            ($entry eq 'samples' || $entry eq 'mean' || $entry eq 'stdev' || $entry eq 'gmean')) {
             $vars->{$name}{type} = 'distribution';
         }
         # Note: If type is already 'histogram', we keep it as histogram
    } else {
         # First time seeing it. Check if summary implies distribution
         my $init_type = 'vector';
         if ($entry eq 'samples' || $entry eq 'mean' || $entry eq 'stdev' || $entry eq 'gmean') {
             $init_type = 'distribution';
         }
         $vars->{$name} = { type => $init_type, entries => { $entry => 1 } };
    }
}

sub manageType {
    my ($name, $new_type, $vars) = @_;

    if (!exists $vars->{$name}) {
        $vars->{$name} = { type => $new_type, entries => {} };
        return;
    }

    my $current_type = $vars->{$name}{type};

    # Type conflict / evolution
    # Upgrade Scalar -> Vector or Distribution or Histogram
    if ($current_type eq 'scalar' && ($new_type eq 'vector' || $new_type eq 'distribution' || $new_type eq 'histogram')) {
        $vars->{$name}{type} = $new_type;
    }
    # Upgrade Vector -> Distribution or Histogram
    elsif ($current_type eq 'vector' && ($new_type eq 'distribution' || $new_type eq 'histogram')) {
        $vars->{$name}{type} = $new_type;
    }
    # Upgrade Distribution -> Histogram (FIX for Issue 1900)
    elsif ($current_type eq 'distribution' && $new_type eq 'histogram') {
        $vars->{$name}{type} = $new_type;
    }
}

sub addEntry {
    my ($name, $entry, $vars) = @_;
    if (defined $entry) {
        $vars->{$name}{entries}->{$entry} = 1;
    }
}

sub processRecords {
    my ($records) = @_;
    foreach my $record (@$records) {
        my $type = $record->{type};
        next if $type eq 'dump';
        my $name = $record->{name};
        my $entry = $record->{scan_entry};
        if ($type eq 'summary') {
            processSummary($name, $entry, \%discovered_vars);
        } else {
            manageType($name, $type, \%discovered_vars);
            addEntry($name, $entry, \%discovered_vars);
        }
    }
}

while (my $line = <$fh>) {
    if (++$line_count > $max_lines) {
        die "Scanner line limit exceeded ($max_lines lines): $filename\n";
    }
    chomp $line;
    next if $line =~ /^$/;
    my $records = TypesFormatRegex::classifyLine($line);
    processRecords($records) if defined $records;
}

processRecords(TypesFormatRegex::finishLineContext());
close($fh);

# Output Results
sub outputResults {
    my ($vars) = @_;
    print "[\n";
    my $first = 1;
    foreach my $name (sort keys %$vars) {
        print ",\n" unless $first;
        $first = 0;

        my $data = $vars->{$name};
        my $type = $data->{type};

        print "  {\n";
        print "    \"name\": \"$name\",\n";
        print "    \"type\": \"$type\"";

        if (scalar keys %{$data->{entries}}) {
            print ",\n    \"entries\": [";
            my @entries = sort keys %{$data->{entries}};
            print join(", ", map { "\"$_\"" } @entries);
            print "]";

            # For distributions, calculate min and max from integer entries
            if ($type eq "distribution") {
                my $min = undef;
                my $max = undef;
                foreach my $e (@entries) {
                    # Check for integer buckets (allow negative)
                    if ($e =~ /^-?\d+$/) {
                        if (!defined $min || $e < $min) { $min = $e; }
                        if (!defined $max || $e > $max) { $max = $e; }
                    }
                }
                if (defined $min) {
                    print ",\n    \"minimum\": $min";
                    print ",\n    \"maximum\": $max";
                }
            }
        }

        print "\n  }";
    }
    print "\n]\n";
}

outputResults(\%discovered_vars);
