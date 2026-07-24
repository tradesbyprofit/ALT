#!/usr/bin/env bash
# uninstall_systemd.sh — Remove ALT Method systemd units
# Use this if "it doesnt work today" and you want manual mode

set -e

echo "=== ALT Method systemd uninstall ==="

sudo systemctl stop alt-daily.service 2>/dev/null || true
sudo systemctl stop alt-daily.timer 2>/dev/null || true
sudo systemctl stop alt-runner.service 2>/dev/null || true
sudo systemctl stop alt-open.service 2>/dev/null || true

sudo systemctl disable alt-daily.timer 2>/dev/null || true
sudo systemctl disable alt-daily.service 2>/dev/null || true
sudo systemctl disable alt-runner.service 2>/dev/null || true
sudo systemctl disable alt-open.service 2>/dev/null || true

sudo rm -f /etc/systemd/system/alt-daily.service
sudo rm -f /etc/systemd/system/alt-daily.timer
sudo rm -f /etc/systemd/system/alt-runner.service
sudo rm -f /etc/systemd/system/alt-open.service

sudo systemctl daemon-reload

echo "✅ Removed systemd units."
echo "Manual mode:"
echo "  nohup python alt_daily.py > runner.log 2>&1 &"
echo "  or"
echo "  python alt_main.py open && nohup python alt_runner.py > runner.log 2>&1 &"
