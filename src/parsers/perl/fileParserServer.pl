#!/usr/bin/perl
#
# Persistent Perl Parser Server
# Stays alive to process multiple parse requests without restart overhead.
# Communicates via STDIN/STDOUT with clear protocol and error handling.
#

use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/libs";
use TypesFormatRegex;

# Enable autoflush for immediate output
$| = 1;

# Log to STDERR for debugging (STDOUT is reserved for results)
sub log_info {
    my ($msg) = @_;
    print STDERR "[PERL-SERVER] INFO: $msg\n";
}

sub log_error {
    my ($msg) = @_;
    print STDERR "[PERL-SERVER] ERROR: $msg\n";
}

sub log_warn {
    my ($msg) = @_;
    print STDERR "[PERL-SERVER] WARN: $msg\n";
}

# Signal readiness
print "READY\n";
log_info("Parser server started and ready for commands");

my $request_count = 0;
my $max_requests = 1000; # Restart after N requests to prevent memory leaks

# Main command loop
while (my $command = <STDIN>) {
    chomp $command;
    $request_count++;
    
    # Check if we should restart (prevent memory bloat)
    if ($request_count > $max_requests) {
        log_warn("Reached max requests ($max_requests), signaling restart needed");
        print "RESTART_NEEDED\n";
        last;
    }
    
    # Parse command
    if ($command =~ /^PARSE\s+(.+)$/) {
        my $args_str = $1;
        my @args = split /\|\|/, $args_str;  # Use || as separator to allow spaces in paths
        
        if (@args < 2) {
            log_error("Invalid PARSE command format: expected 'PARSE <file>||<filter1>||<filter2>...'");
            print "ERROR Invalid command format\n";
            print "END_PARSE\n";
            next;
        }
        
        my $filename = shift @args;
        my @filters = @args;
        
        log_info("Processing request #$request_count: file=$filename, filters=" . scalar(@filters));
        
        # Validate file exists
        unless (-f $filename) {
            log_error("File not found: $filename");
            print "ERROR File not found: $filename\n";
            print "END_PARSE\n";
            next;
        }
        
        # Validate file is readable
        unless (-r $filename) {
            log_error("File not readable: $filename");
            print "ERROR File not readable: $filename\n";
            print "END_PARSE\n";
            next;
        }
        
        # Set filter regexes
        eval {
            setFilterRegexes(@filters);
        };
        if ($@) {
            log_error("Failed to compile filter regexes: $@");
            print "ERROR Invalid regex filters: $@\n";
            print "END_PARSE\n";
            next;
        }
        
        # Open and parse file
        my $line_count = 0;
        my $match_count = 0;
        
        eval {
            open(my $fh, '<:raw', $filename) or die "Cannot open file: $!";
            
            while (my $line = <$fh>) {
                chomp $line;
                $line_count++;
                
                # Skip empty lines
                next if $line =~ /^\s*$/;
                
                # Parse and print - parseAndPrintLineWithFormat outputs directly
                my $before_count = $match_count;
                parseAndPrintLineWithFormat($line);
                
                # Safety limit
                if ($line_count > 10_000_000) {
                    log_warn("File too large, stopping at 10M lines");
                    last;
                }
            }
            
            close($fh);
        };
        
        if ($@) {
            log_error("Error during parsing: $@");
            print "ERROR Parsing failed: $@\n";
        } else {
            log_info("Completed parsing: $line_count lines processed");
        }
        
        # Signal completion
        print "END_PARSE\n";
    }
    elsif ($command eq "PING") {
        # Health check
        print "PONG\n";
        log_info("Health check: PONG");
    }
    elsif ($command eq "STATS") {
        # Return statistics
        print "REQUESTS $request_count\n";
        print "END_STATS\n";
        log_info("Stats requested: $request_count requests served");
    }
    elsif ($command eq "SHUTDOWN") {
        log_info("Shutdown command received, exiting gracefully");
        print "GOODBYE\n";
        last;
    }
    else {
        log_warn("Unknown command: $command");
        print "ERROR Unknown command: $command\n";
    }
}

log_info("Parser server shutting down after $request_count requests");
exit 0;
