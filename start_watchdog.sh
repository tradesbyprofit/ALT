#!/bin/bash
cd /home/user
pkill -f alt_watchdog.py || true
PYTHONUNBUFFERED=1 nohup python -u alt_watchdog.py --loop 60 > watchdog.log 2>&1 &
echo $! > watchdog.pid
echo "Watchdog PID $(cat watchdog.pid)"
cat watchdog.log
