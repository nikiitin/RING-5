#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/perl/libs";
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

while (my $line = <$fh>) {
    chomp $line;
    next if $line =~ /^$/;
    next if $line =~ /^---/; # standard gem5 divider

    my $info = TypesFormatRegex::classifyLine($line);
    next unless $info;

    my $name = $info->{name};
    my $type = $info->{type};
    my $entry = $info->{entry};

    # Type refinement logic (mirroring Python logic)
    if ($type eq 'Summary') {
        # Vector/Dist summaries are treated as vector entries if possible
        if (exists $discovered_vars{$name}) {
             $discovered_vars{$name}{entries}->{$entry} = 1;
             
             if ($discovered_vars{$name}{type} eq 'Scalar') {
                 $discovered_vars{$name}{type} = 'Vector';
             }
        } else {
             # First time seeing it. Assume Vector with entry for now.
             $discovered_vars{$name} = { type => 'Vector', entries => { $entry => 1 } };
        }
        next;
    }

    # Config hint check
    if ($type eq 'Scalar' && exists $config_vars{$name}) {
        $type = 'Configuration';
    }

    if (!exists $discovered_vars{$name}) {
        $discovered_vars{$name} = { type => $type, entries => {} };
    } else {
        # Type conflict / evolution
        if ($discovered_vars{$name}{type} eq 'Scalar' && ($type eq 'Vector' || $type eq 'Distribution')) {
            $discovered_vars{$name}{type} = $type;
        }
    }

    if (defined $entry) {
        $discovered_vars{$name}{entries}->{$entry} = 1;
    }
}

close($fh);

# Convert to JSON list
print "[\n";
my $first = 1;
foreach my $name (sort keys %discovered_vars) {
    print ",\n" unless $first;
    $first = 0;
    
    my $data = $discovered_vars{$name};
    my $type = lc($data->{type});
    $type = "configuration" if $type eq "configuration";
    
    print "  {\n";
    print "    \"name\": \"$name\",\n";
    print "    \"type\": \"$type\"";
    
    if (scalar keys %{$data->{entries}}) {
        print ",\n    \"entries\": [";
        my @entries = sort keys %{$data->{entries}};
        print join(", ", map { "\"$_\"" } @entries);
        print "]";
    }
    
    print "\n  }";
}
print "\n]\n";
