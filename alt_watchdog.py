#!/usr/bin/env python3
"""
alt_watchdog.py — Dallas CT watchdog for ALT Method

Pings Telegram if:
  1) Runner NOT running automatically but games still open (stale/dead)
  2) Heartbeat hits 0 — all games closed (completion ping)
  3) Heartbeat stale — no log update in 10 min while games still open

Usage:
  python alt_watchdog.py --once        # single check (for cron)
  python alt_watchdog.py --loop        # loop every 60s forever
  python alt_watchdog.py --loop 30     # loop every 30s

Designed to run alongside alt_runner.py / alt_daily.py
Sends alerts labeled ALT Method.

State file .watchdog_state.json prevents spam (won't re-alert same condition within 30 min)
"""
from __future__ import annotations

import argparse, json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# import our main for telegram + db
import alt_main as am

TZ = ZoneInfo(am.CONFIG["timezone"])
STATE_FILE = Path(".watchdog_state.json")
PID_FILE = Path("runner.pid")
LOG_FILE = Path("runner.log")
HEARTBEAT_STALE_MIN = 10
ALERT_COOLDOWN_MIN = 30  # don't spam same alert more often

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {}
    return {}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

def should_alert(state, key):
    """Check cooldown — allow alert if never sent or >30 min ago"""
    now = datetime.now(timezone.utc).timestamp()
    last = state.get(key, 0)
    if now - last > ALERT_COOLDOWN_MIN*60:
        state[key]=now
        save_state(state)
        return True
    return False

def is_runner_alive():
    if not PID_FILE.exists():
        # also check ps
        import subprocess
        out = subprocess.getoutput("ps aux | grep -E 'alt_runner|alt_daily' | grep -v grep | grep -v watchdog")
        return bool(out.strip()), None, out.strip()
    try:
        pid = int(PID_FILE.read_text().strip())
        # check if process exists
        os.kill(pid, 0)
        return True, pid, f"pid {pid}"
    except Exception:
        return False, None, "pid file stale"

def get_open_count():
    try:
        conn = am.get_conn()
        row = conn.execute("SELECT COUNT(*) FROM games WHERE status='open'").fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        return -1

def get_log_age_minutes():
    if not LOG_FILE.exists():
        return 999
    mtime = LOG_FILE.stat().st_mtime
    age = (time.time() - mtime)/60.0
    return age

def get_last_heartbeat():
    """Parse last heartbeat from log if possible"""
    if not LOG_FILE.exists():
        return None
    try:
        lines = LOG_FILE.read_text().splitlines()[-50:]
        for l in reversed(lines):
            if "heartbeat" in l.lower() or "open" in l.lower():
                return l
        return lines[-1] if lines else None
    except Exception:
        return None

def send_watchdog_telegram(text, code):
    """Send telegram with ALT Method watchdog label"""
    # format with HTML
    full = f"🚨 <b>ALT Method Watchdog</b> · {code}\n\n{text}\n\n⏱ {datetime.now(TZ).strftime('%H:%M:%S %Z')}"
    return am.send_telegram(full)

def check_once(state, verbose=True):
    now_ct = datetime.now(TZ).strftime("%H:%M:%S")
    alive, pid, info = is_runner_alive()
    open_cnt = get_open_count()
    log_age = get_log_age_minutes()
    last_hb = get_last_heartbeat()

    if verbose:
        print(f"[{now_ct}] Watchdog check — alive={alive} ({info}) open={open_cnt} log_age={log_age:.1f}m")
        if last_hb:
            print(f"  last log: {last_hb[:120]}")

    alerts = []

    # CASE 1: Heartbeat hits 0 — all games closed → completion ping (this is GOOD, not error)
    if open_cnt == 0:
        if should_alert(state, "all_closed"):
            msg = f"🏁 <b>All games closed</b>\nSlate done — {am.CONFIG['storage']['sqlite_path']} shows 0 open.\nRunner can exit.\n\nToday: {datetime.now(TZ).strftime('%Y-%m-%d')}"
            print(f"  → completion: open=0, sending Telegram")
            send_watchdog_telegram(msg, "COMPLETE")
            alerts.append("completion")
        else:
            if verbose:
                print("  completion already alerted (cooldown)")

    # CASE 2: Runner NOT running automatically but games still open → CRITICAL
    if not alive and open_cnt > 0:
        if should_alert(state, "runner_down"):
            msg = (f"⚠️ <b>Runner DOWN</b> but {open_cnt} game(s) still open!\n"
                   f"PID file: {info}\n"
                   f"Log age: {log_age:.1f} min\n"
                   f"Last: {last_hb or 'no log'}\n\n"
                   f"Fix:\n"
                   f"  pkill -f alt_daily; nohup python alt_daily.py > runner.log 2>&1 &\n"
                   f"  or: systemctl start alt-daily.service")
            print(f"  → CRITICAL: runner down with {open_cnt} open, sending Telegram")
            send_watchdog_telegram(msg, "DOWN")
            alerts.append("down")
        else:
            if verbose:
                print("  runner down already alerted (cooldown)")

    # CASE 3: Heartbeat stale — log not updated in >10 min while games open → WARNING
    if alive and open_cnt > 0 and log_age > HEARTBEAT_STALE_MIN:
        if should_alert(state, "stale"):
            msg = (f"⚠️ <b>Heartbeat stale</b> — {log_age:.0f} min no update\n"
                   f"Runner alive={alive} but may be stuck\n"
                   f"Open: {open_cnt}\n"
                   f"Last log: {last_hb}\n\n"
                   f"Check: tail -f runner.log\n"
                   f"Restart if needed")
            print(f"  → WARNING: stale heartbeat {log_age:.0f}m, sending Telegram")
            send_watchdog_telegram(msg, "STALE")
            alerts.append("stale")

    if not alerts and verbose:
        print("  ✅ all good — no alert needed")

    return alerts

def main():
    parser = argparse.ArgumentParser(description="ALT Method watchdog — pings if not running or heartbeat 0")
    parser.add_argument("--once", action="store_true", help="single check")
    parser.add_argument("--loop", nargs="?", const=60, type=int, help="loop every N seconds (default 60)")
    args = parser.parse_args()

    state = load_state()

    if args.once:
        check_once(state, verbose=True)
        return 0

    interval = args.loop if args.loop else 60
    print(f"🐶 Watchdog looping every {interval}s — will ping Telegram if runner dies or heartbeat hits 0")
    print(f"   Dallas time {datetime.now(TZ).strftime('%H:%M:%S %Z')}")
    try:
        while True:
            state = load_state()
            check_once(state, verbose=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatchdog stopped")
    return 0

if __name__ == "__main__":
    sys.exit(main())
