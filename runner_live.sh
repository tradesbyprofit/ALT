#!/bin/bash
cd /home/user
echo "Starting ALT Method runner for remaining 14 games..."
echo "Now Dallas time: $(TZ='America/Chicago' date)"
echo "Next: Cubs@Pirates 17:40 CT in ~153m"
echo "Logs -> runner.log"
nohup python alt_runner.py > runner.log 2>&1 &
echo $! > runner.pid
echo "PID $(cat runner.pid) started"
tail -20 runner.log || true
