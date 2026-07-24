#!/usr/bin/env python3
"""
alt_runner.py — keeps the ALT Method T-5 closing pull running automatically.

Polls every POLL_SECONDS. Whenever a frozen game enters the 1-5 minute
pre-start window, it captures the closing snapshot and pinks any picks that
pass the margin-drop rule straight to Telegram (labeled "ALT Method").
Idempotent: each game is closed exactly once, then skipped. Exits when the
entire slate is closed.

Usage:
    python alt_runner.py [slate_date]        # default: today (America/Chicago)

Run in the background so it survives closing the terminal:
    nohup python alt_runner.py > runner.log 2>&1 &

Or keep it on screen with tmux / screen:
    tmux new -s altrunner 'python alt_runner.py'
"""
from __future__ import annotations

import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import alt_main as am

POLL_SECONDS = 30          # how often to check the window
HEARTBEAT_EVERY = 10       # print a status heartbeat every N polls (~5 min)

TZ = ZoneInfo(am.CONFIG["timezone"])
_stop = False


def _handle_stop(signum, frame):
    global _stop
    _stop = True
    log("stop signal received — finishing current cycle and exiting.")


def log(msg: str) -> None:
    ts = datetime.now(TZ).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def open_count(conn, slate: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM games WHERE slate_date=? AND status='open';",
        (slate,),
    ).fetchone()[0]


def next_game(conn, slate: str):
    return conn.execute(
        "SELECT away_team, home_team, start_utc FROM games "
        "WHERE slate_date=? AND status='open' ORDER BY start_utc LIMIT 1;",
        (slate,),
    ).fetchone()


def main() -> int:
    slate = (sys.argv[1] if len(sys.argv) > 1
             else datetime.now(TZ).strftime("%Y-%m-%d"))
    am.init_db()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    tg = am.CONFIG["alerts"]["telegram"]
    log(f"🎯 ALT Method runner started")
    log(f"   slate: {slate}  ·  poll every {POLL_SECONDS}s  ·  "
        f"window T-{am.CONFIG['capture']['closing_window_max']}..T-{am.CONFIG['capture']['closing_window_min']}")
    log(f"   telegram: {'ON → chat ' + str(tg.get('chat_id')) if tg.get('enabled') else 'OFF'}")

    poll = 0
    total_closed = 0
    while not _stop:
        poll += 1
        try:
            closed = am.run_close_cycle(quiet=True)
            if closed:
                total_closed += closed
                log(f"✅ closed {closed} game(s) this cycle (total {total_closed}) — picks pinged")
        except Exception as e:  # never let one bad cycle kill the runner
            log(f"⚠️  cycle error (will retry): {e!r}")

        conn = am.get_conn()
        remaining = open_count(conn, slate)
        if remaining == 0:
            conn.close()
            log(f"🏁 all games on {slate} closed ({total_closed} handled). runner exiting.")
            # ping completion so you know heartbeat hit 0
            try:
                am.send_telegram(f"🏁 <b>ALT Method</b> · COMPLETE · {slate}\nAll {total_closed} games closed. Heartbeat 0 — runner exiting.\n⏱ {datetime.now(TZ).strftime('%H:%M %Z')}")
            except Exception:
                pass
            return 0

        if poll % HEARTBEAT_EVERY == 0:
            ng = next_game(conn, slate)
            if ng:
                from datetime import timezone
                mins = ((datetime.fromisoformat(ng["start_utc"])
                         - datetime.now(timezone.utc)).total_seconds() / 60.0)
                log(f"💓 heartbeat — {remaining} open · next: "
                    f"{ng['away_team']} @ {ng['home_team']} in {mins:+.0f} min")
        conn.close()

        # sleep in small slices so a stop signal is honored quickly
        for _ in range(POLL_SECONDS):
            if _stop:
                break
            time.sleep(1)

    log(f"runner stopped ({total_closed} closed this run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
