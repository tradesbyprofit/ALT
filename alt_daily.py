#!/usr/bin/env python3
"""
alt_daily.py — Daily orchestrator for ALT Method (Dallas CT)

Does BOTH steps automatically:
  1) 7 PM CT opening pull (freeze all alternates for today's slate)
  2) T-5 runner (poll every 30s until all games close, ping Telegram)

Usage:
  python alt_daily.py                # uses today in America/Chicago
  python alt_daily.py 2026-07-24     # specific slate

Designed to be called by systemd timer at 19:00 CT daily.
If telegram is configured, picks are labeled "ALT Method" and sent at close.

Idempotent: you can run open multiple times (ON CONFLICT updates).
Runner exits cleanly when slate is fully closed.
"""
from __future__ import annotations

import signal
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import alt_main as am

TZ = ZoneInfo(am.CONFIG["timezone"])
POLL_SECONDS = 30
HEARTBEAT_EVERY = 10  # every ~5 min

_stop = False

def _handle_stop(signum, frame):
    global _stop
    _stop = True
    log("stop signal — exiting after current cycle")

def log(msg: str):
    ts = datetime.now(TZ).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print("Usage: python alt_daily.py [YYYY-MM-DD]  # Dallas CT daily open + T-5 runner")
        return 0
    slate = (sys.argv[1] if len(sys.argv) > 1 else datetime.now(TZ).strftime("%Y-%m-%d"))

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    am.init_db()
    tg = am.CONFIG["alerts"]["telegram"]

    log(f"🎯 ALT Method DAILY started")
    log(f"   slate {slate} | tz {am.CONFIG['timezone']} | Dallas CT 7PM trigger")
    log(f"   telegram: {'ON → ' + str(tg.get('chat_id')) if tg.get('enabled') else 'OFF'}")
    log("")

    # STEP 1: OPENING PULL
    log(f"📥 Step 1 — Opening pull for {slate}")
    rc = am.cmd_open([slate])
    if rc != 0:
        log(f"⚠️ open returned {rc} — will still try to run closer")
    else:
        conn = am.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM games WHERE slate_date=? AND status='open';", (slate,)).fetchone()[0]
        conn.close()
        log(f"🔒 Frozen: {n} open games for {slate}")
    log("")

    # STEP 2: T-5 RUNNER LOOP
    log(f"📤 Step 2 — T-5 runner active (window T-{am.CONFIG['capture']['closing_window_max']}..T-{am.CONFIG['capture']['closing_window_min']})")
    poll = 0
    total_closed = 0

    while not _stop:
        poll += 1
        try:
            closed = am.run_close_cycle(quiet=True)
            if closed:
                total_closed += closed
                log(f"✅ closed {closed} game(s) this cycle (total {total_closed} today) — ALT Method ping sent if picks passed")
        except Exception as e:
            log(f"⚠️ cycle error, will retry: {e!r}")

        conn = am.get_conn()
        remaining = conn.execute("SELECT COUNT(*) FROM games WHERE slate_date=? AND status='open';", (slate,)).fetchone()[0]
        if remaining == 0:
            conn.close()
            log(f"🏁 ALL CLOSED — {total_closed} handled today. Daily run complete.")
            try:
                am.send_telegram(f"🏁 <b>ALT Method</b> · COMPLETE · {slate}\nAll {total_closed} games closed. Heartbeat 0 — daily run done.\n⏱ {datetime.now(TZ).strftime('%H:%M %Z')}")
            except Exception:
                pass
            return 0

        if poll % HEARTBEAT_EVERY == 0:
            row = conn.execute(
                "SELECT away_team, home_team, start_utc FROM games WHERE slate_date=? AND status='open' ORDER BY start_utc LIMIT 1;",
                (slate,)
            ).fetchone()
            if row:
                mins = (datetime.fromisoformat(row["start_utc"]) - datetime.now(timezone.utc)).total_seconds() / 60.0
                log(f"💓 heartbeat — {remaining} open · next {row['away_team']} @ {row['home_team']} in {mins:+.0f} min")
        conn.close()

        for _ in range(POLL_SECONDS):
            if _stop:
                break
            time.sleep(1)

    log(f"runner stopped by signal ({total_closed} closed)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
