#include <Rcpp.h>
#include "R_ext/RStartup.h"
#include <iostream>
using namespace Rcpp;

// [[Rcpp::export]]
void setCommandArgs(std::vector<std::string> args) {
    std::vector<char*> argvec(args.size());
    for (size_t i = 0; i < args.size(); i++) {
        argvec[i] = const_cast<char*>(args[i].c_str());
    }
    R_set_command_line_arguments(args.size(),
        static_cast<char**>(&(argvec[0])));
}