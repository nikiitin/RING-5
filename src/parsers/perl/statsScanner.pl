#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/libs";
use TypesFormatRegex;

# Arguments:
# 1. stats_file
# 2. (Optional) config variables list (comma separated) for detection hints

my $filename = shift or die "Usage: statsScanner.pl <stats_file> [config_vars]\n";
my $config_vars_str = shift || "";
my %config_vars = map { $_ => 1 } split(',', $config_vars_str);

open(my $fh, '<', $filename) or die "Could not open file '$filename' $!";

# Data structure to hold discovered variables
# { name => { type => type, entries => [entries...] } }
my %discovered_vars;

# Helper globals from TypesFormatRegex
# We access regexes indirectly by calling classifyLine provided by TypesFormatRegex.
# We set a catch-all filter to scan all lines.
TypesFormatRegex::setFilterRegexes(".*");



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
         if ($vars->{$name}{type} eq 'vector' &&
            ($entry eq 'samples' || $entry eq 'mean' || $entry eq 'stdev' || $entry eq 'gmean')) {
             $vars->{$name}{type} = 'distribution';
         }
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

while (my $line = <$fh>) {
    # print STDERR "DEBUG: $line\n";
    chomp $line;
    # $line =~ s/\s+$//;
    next if $line =~ /^$/;
    next if $line =~ /^---/; # standard gem5 divider

    my $info = TypesFormatRegex::classifyLine($line);
    next unless $info;

    my $name = $info->{name};
    my $type = $info->{type};
    my $entry = $info->{entry};

    if ($type eq 'summary') {
        processSummary($name, $entry, \%discovered_vars);
        next;
    }

    # Config hint check
    if ($type eq 'scalar' && exists $config_vars{$name}) {
        $type = 'configuration';
    }

    manageType($name, $type, \%discovered_vars);
    addEntry($name, $entry, \%discovered_vars);
}

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
