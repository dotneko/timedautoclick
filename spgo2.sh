#!/usr/bin/env bash

source config.local
echo STARTcmd = $START
echo CLOSEcmd = $CLOSE
uv run main2.py $1 -r 2 $START $CLOSE $CLOSE
