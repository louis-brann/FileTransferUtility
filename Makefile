#
# Makefile for CS125 Lab 3 - File Transfer Utility
# Modified by: Ben Goldberg and Louis Brann
# 

# ----- Make Variables ----- 

CXXFLAGS  = -g -std=c++11 -Wall -Wextra -Wdocumentation -pedantic
CXX   = g++
GTEST_LIB = -lgtest -lgtest_main

TARGETS   =     ftu

# ----- Make Rules -----

all:    $(TARGETS)

clean:
	rm -f $(TARGETS) *.o

ftu: ftu.o 
	$(CXX) $(CXXFLAGS) -o ftu $^

# ------ Dependences (.cpp -> .o using default Makefile rule) -----

ftu.o: ftu.cpp 

