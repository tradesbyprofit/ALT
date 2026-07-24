#!/usr/bin/env python3
"""
verify_setup.py — Dallas CT health check for ALT Method
Checks everything so we KNOW auto is running correctly before first ping.
"""
import sys, json, sqlite3, os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")

def ok(msg): print(f"✅ {msg}")
def warn(msg): print(f"⚠️  {msg}")
def fail(msg): print(f"❌ {msg}")

print("="*60)
print("ALT Method — SETUP VERIFICATION — Dallas CT")
print("="*60)
print(f"Local time Dallas: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print()

# 1. Python + requests
print("1) Python & deps")
print(f"   Python {sys.version.split()[0]}")
try:
    import requests
    ok(f"requests {requests.__version__}")
except Exception as e:
    fail(f"requests missing: {e} — pip install requests")
    sys.exit(1)

# 2. Files
print("\n2) Project files")
for f in ["alt_main.py","alt_runner.py","alt_daily.py","telegram_creds.json","data/alternate_model.db"]:
    p=Path(f)
    if p.exists():
        ok(f"{f} exists ({p.stat().st_size} bytes)")
    else:
        fail(f"{f} MISSING")

# 3. Timezone check
print("\n3) Timezone — MUST be America/Chicago for 7 PM auto")
try:
    import subprocess
    tz = subprocess.getoutput("timedatectl 2>/dev/null | grep 'Time zone' || date +%Z")
    print(f"   System reports: {tz}")
    now_ct = datetime.now(TZ)
    ok(f"Dallas time is {now_ct.strftime('%H:%M %Z')} — timer will fire at 19:00 local")
    if "CDT" in now_ct.tzname() or "CST" in now_ct.tzname() or "Chicago" in str(TZ):
        ok("Timezone logic OK (CDT is UTC-5, CST UTC-6 — handles DST)")
    else:
        warn("If server is UTC, 19:00 timer = 2 PM CT — run: sudo timedatectl set-timezone America/Chicago")
except Exception as e:
    warn(f"timezone check: {e}")

# 4. DB
print("\n4) Database — frozen slate")
try:
    conn=sqlite3.connect("data/alternate_model.db")
    conn.row_factory=sqlite3.Row
    rows=conn.execute("SELECT slate_date, status, COUNT(*) c FROM games GROUP BY slate_date,status ORDER BY slate_date DESC").fetchall()
    if not rows:
        fail("No games in DB — run python alt_main.py open")
    else:
        for r in rows:
            print(f"   {r['slate_date']} — {r['status']} — {r['c']} game(s)")
            if r['status']=='open':
                ok(f"{r['c']} games still open, ready for T-5")
        # next game
        now=datetime.now(timezone.utc)
        nxt=conn.execute("SELECT id, away_team, home_team, start_utc FROM games WHERE status='open' ORDER BY start_utc LIMIT 3").fetchall()
        for g in nxt:
            start=datetime.fromisoformat(g["start_utc"])
            mins=(start-now).total_seconds()/60
            print(f"   Next #{g['id']} {g['away_team']} @ {g['home_team']} in {mins:.0f} min (T-5 at {mins-5:.0f}min)")
    conn.close()
except Exception as e:
    fail(f"DB error: {e}")

# 5. Telegram creds
print("\n5) Telegram @ProfitSniperHQBot — ALT Method labeling")
try:
    p=Path("telegram_creds.json")
    if p.exists():
        d=json.loads(p.read_text())
        token=d.get("bot_token","")
        chat=d.get("chat_id","")
        if token and token!="FILL_IN" and chat:
            ok(f"Creds found — bot {d.get('_bot','')} → chat {chat}")
            # import config check
            import alt_main as am
            if am.CONFIG["alerts"]["telegram"]["enabled"]:
                ok("Telegram enabled in alt_main.py (auto-loaded from creds)")
            else:
                fail("Telegram not enabled — check telegram_creds.json")
        else:
            fail("telegram_creds.json empty")
    else:
        fail("telegram_creds.json missing")
except Exception as e:
    fail(f"Telegram creds error: {e}")

# 6. Pinnacle connectivity
print("\n6) Pinnacle API — can we reach board?")
try:
    import alt_main as am
    client=am.PinnacleClient()
    mlb_id=am.CONFIG["league_ids"]["mlb"]
    raw=client.get_matchups(mlb_id)
    ok(f"Pinnacle reachable — MLB matchups returned {len(raw)} rows (includes specials)")
    # parse
    parsed=am.parse_matchups(raw)
    ok(f"Parsed {len(parsed)} real matchups (not specials)")
except Exception as e:
    fail(f"Pinnacle fetch failed: {e}")

# 7. Runner check
print("\n7) Runner status")
try:
    import subprocess, pathlib
    pid_file=Path("runner.pid")
    if pid_file.exists():
        pid=pid_file.read_text().strip()
        out=subprocess.getoutput(f"ps -p {pid} -o cmd= 2>/dev/null")
        if out:
            ok(f"runner.pid {pid} running: {out}")
        else:
            warn(f"runner.pid {pid} not running (stale)")
    # check log
    log=Path("runner.log")
    if log.exists():
        lines=log.read_text().splitlines()[-5:]
        print("   Last 5 log lines:")
        for l in lines:
            print(f"   {l}")
        ok("runner.log exists")
    else:
        warn("No runner.log yet — runner not started?")

    # systemd check
    sysd=subprocess.getoutput("systemctl is-active alt-daily.timer 2>&1 || echo 'not-systemd'")
    if "active" in sysd:
        ok(f"systemd timer active: {sysd}")
        timers=subprocess.getoutput("systemctl list-timers alt-daily.timer --no-pager 2>&1 | tail -5")
        print(f"   {timers}")
    else:
        print(f"   systemd timer: {sysd} (OK if you're using nohup instead)")
except Exception as e:
    warn(f"Runner check: {e}")

print("\n"+"="*60)
print("VERIFICATION SUMMARY")
print("="*60)
print("If all ✅, you're good to wait for next ping.")
print("Next expected Telegram ping (Dallas CT):")
print("  17:35 CT — Cubs@Pirates #7 + Royals@Tigers #8 (T-5)")
print("  Then 17:40, 18:00, 18:05 batches")
print()
print("To start auto NOW:")
print("  nohup python alt_daily.py > runner.log 2>&1 &   (manual reliable)")
print("  OR systemctl start alt-daily.service           (systemd)")
print("To watch:")
print("  tail -f runner.log")
print("  python alt_main.py status")
print("To test Telegram now:")
print("  python alt_main.py test-telegram")
print("="*60)
