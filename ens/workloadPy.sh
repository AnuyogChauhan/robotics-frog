#!/bin/bash

# ENS Python workload launcher

cd /frog
export LD_LIBRARY_PATH=/frog
echo Starting Python runtime $1
#python3 enswmain.py $1
python2.7 enswmain.py $1
#python server.py 


