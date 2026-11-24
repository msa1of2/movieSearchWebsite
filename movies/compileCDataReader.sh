#!/bin/bash
#Compiles the movieDataReader.c for python's use for faster file lookups
clang -shared -fPIC -o dataExtractor.so movieDataReader.c
