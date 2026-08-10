#!/bin/bash
source config.local
echo STARTcmd = $START
echo CLOSEcmd = $CLOSE
./timed_autoclick.py $1 -r 2 $START $CLOSE $CLOSE
