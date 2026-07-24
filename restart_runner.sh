#!/bin/bash
cd /home/user
pkill -f alt_runner.py || true
pkill -f alt_daily.py || true
rm -f runner.pid
echo "Restarting with unbuffered..."
PYTHONUNBUFFERED=1 nohup python -u alt_runner.py > runner.log 2>&1 &
echo $! > runner.pid
sleep 2
cat runner.log
ps -p $(cat runner.pid) -o pid,etime,cmd
