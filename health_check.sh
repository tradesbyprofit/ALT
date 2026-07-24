#!/usr/bin/env bash
# health_check.sh — Dallas CT quick health check + auto start

set -e
cd "$(dirname "$0")"

echo "=== ALT Method — Dallas CT Health Check ==="
echo "Dallas time: $(TZ='America/Chicago' date)"
echo "UTC time: $(date -u)"
echo ""

# python check
python3 verify_setup.py

echo ""
echo "=== Quick commands ==="
echo "Current status:"
python3 alt_main.py status

echo ""
echo "Is runner alive?"
if [ -f runner.pid ]; then
  PID=$(cat runner.pid)
  if ps -p $PID > /dev/null; then
    echo "✅ runner PID $PID running"
    ps -p $PID -o pid,cmd,%cpu,%mem,etime
  else
    echo "❌ PID file stale — no process $PID"
  fi
else
  echo "No runner.pid — checking ps..."
  ps aux | grep -E "alt_runner|alt_daily" | grep -v grep || echo "No runner process found"
fi

echo ""
echo "Logs:"
if [ -f runner.log ]; then
  echo "--- last 15 lines runner.log ---"
  tail -15 runner.log
else
  echo "No runner.log"
fi

echo ""
echo "=== To start auto ==="
echo "Manual (reliable, any OS):"
echo "  nohup python alt_daily.py > runner.log 2>&1 &"
echo "  tail -f runner.log"
echo ""
echo "Systemd (Linux VPS):"
echo "  ./install_systemd.sh"
echo "  systemctl status alt-daily.timer"
echo "  systemctl start alt-daily.service  # run now"
echo ""
echo "If first ping fails, check:"
echo "  1. Telegram: python alt_main.py test-telegram"
echo "  2. Pinnacle: python -c 'import alt_main; c=alt_main.PinnacleClient(); print(len(c.get_matchups(246)))'"
echo "  3. DB: python alt_main.py status"
echo "  4. Timezone: timedatectl"
