#!/bin/bash

while true;
do
    if [ -e config.json ]; then
        echo "Starting WTT-Bridge..."
        ./__env/bin/python3 run.py
    else
        echo "config.json does not exist. Please run setup.sh first!"
    fi
done
