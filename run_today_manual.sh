#!/usr/bin/env bash
# run_today_manual.sh — Fallback manual run for Dallas today
# Use if systemd doesn't work today as you said
#
# Dallas, TX — slate 2026-07-24 has 15 MLB games starting 15:10 to 21:15 CT
# This script does open (if not done) + starts T-5 runner in background

set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

SLATE=${1:-$(TZ='America/Chicago' date +%Y-%m-%d)}

echo "=== ALT Method MANUAL run — Dallas CT ==="
echo "Slate: $SLATE"
echo "Project: $PROJECT_DIR"
echo ""

# check venv / python
PYTHON=python3
if [[ -f ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
fi

echo "1) Checking Telegram..."
$PYTHON alt_main.py test-telegram

echo ""
echo "2) Ensuring slate frozen (open)..."
$PYTHON alt_main.py open $SLATE
$PYTHON alt_main.py status

echo ""
echo "3) Starting T-5 runner in background..."
echo "   Logs: $PROJECT_DIR/runner.log"
echo "   Stop: pkill -f alt_runner.py  OR  pkill -f alt_daily.py"

# Choose daily orchestrator OR just runner — daily does both again safely
nohup $PYTHON alt_daily.py $SLATE > runner.log 2>&1 &
PID=$!

echo ""
echo "✅ Runner PID $PID — now polling every 30s"
echo "   tail -f runner.log"
echo "   Games today: 15:10 Rockies@Brewers #15 · 17:40 Cubs@Pirates #7 ... 21:15 Angels@Giants #14 CT"
echo "   Expect Telegram pings labeled '🎯 ALT Method' at T-5 for each game that passes margin-drop rule"
echo ""
echo "To grade tonight after games:"
echo "  python alt_main.py report $SLATE"
echo "  python alt_main.py compare $SLATE"
