#!/usr/bin/env bash
# install_systemd.sh — Install ALT Method daily automation (Dallas CT)
# Run on YOUR Linux server / VPS (not in Arena sandbox)
#
# Usage:
#   chmod +x install_systemd.sh
#   ./install_systemd.sh

set -e

PROJECT_DIR="$(pwd)"
USER_NAME="$(whoami)"
PYTHON_BIN="$(which python3)"

echo "=== ALT Method systemd installer ==="
echo "Project: $PROJECT_DIR"
echo "User: $USER_NAME"
echo "Python: $PYTHON_BIN"
echo "Timezone should be America/Chicago (Dallas)"
echo ""

# Check timezone
CURRENT_TZ=$(timedatectl 2>/dev/null | grep "Time zone" | awk '{print $3}' || echo "unknown")
echo "Current system timezone: $CURRENT_TZ"
if [[ "$CURRENT_TZ" != "America/Chicago" ]]; then
  echo "⚠️  Recommended: sudo timedatectl set-timezone America/Chicago"
  read -p "Set it now? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    sudo timedatectl set-timezone America/Chicago
    echo "✅ Timezone set to America/Chicago"
  else
    echo "Continuing with current timezone — timer will fire at 19:00 in $CURRENT_TZ"
  fi
fi
echo ""

# Patch service files with real paths
for svc in alt-daily.service alt-runner.service alt-open.service; do
  if [[ -f "$svc" ]]; then
    sed -i "s|User=YOUR_USER|User=$USER_NAME|g" "$svc"
    sed -i "s|/home/YOUR_USER/alt-line-clv|$PROJECT_DIR|g" "$svc"
    sed -i "s|/usr/bin/python3|$PYTHON_BIN|g" "$svc"
    # restore placeholder for reruns
    # actually keep edited version; install will copy it
  fi
done

# create log files if using file logging variant
touch "$PROJECT_DIR/runner.log" "$PROJECT_DIR/open.log" 2>/dev/null || true

echo "Installing systemd units..."
sudo cp alt-daily.service /etc/systemd/system/
sudo cp alt-daily.timer /etc/systemd/system/
sudo cp alt-open.service /etc/systemd/system/ 2>/dev/null || true
sudo cp alt-runner.service /etc/systemd/system/ 2>/dev/null || true
sudo cp alt-watchdog.service /etc/systemd/system/ 2>/dev/null || true

sudo systemctl daemon-reload

echo ""
echo "Enabling daily timer (7 PM CT)..."
sudo systemctl enable --now alt-daily.timer
echo "Enabling watchdog (pings if runner dies or heartbeat 0)..."
sudo systemctl enable --now alt-watchdog.service

echo ""
echo "✅ Installed!"
echo ""
echo "Check status:"
echo "  systemctl list-timers alt-daily.timer"
echo "  systemctl status alt-daily.timer"
echo "  journalctl -u alt-daily.service -f   # live logs"
echo "  tail -f $PROJECT_DIR/runner.log     # if you use file logging"
echo ""
echo "Manual test right now (simulate 7 PM pull):"
echo "  systemctl start alt-daily.service"
echo ""
echo "Tonight's flow will be automatic:"
echo "  19:00 CT — open freeze"
echo "  then runner polls every 30s, pings Telegram as ALT Method at T-5"
