#!/bin/sh

mkdir -p build
python3 /bin/sphinx-build -bhtml ./source ./build 
