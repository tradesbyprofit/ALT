# Runner + Watchdog — Dallas Automatic + Ping on Fail / Heartbeat 0

**Your request:** "ping me if its not running automatically and the heart beat hits 0"

Built and tested live now.

## Current state in Dallas CT (2026-07-24)

- **First batch DONE:** #15 Rockies@Brewers 15:10 CT — closed, Telegram sent Milwaukee -2.5 (+125)
- **Runner:** PID 1636 alive, unbuffered, 14 open games
  - Next T-5: 17:35 CT → Cubs@Pirates #7 + Royals@Tigers #8
- **Watchdog:** PID 1650 looping every 60s, monitoring runner + heartbeat

```
[16:24:36] Watchdog check — alive=True (pid 1636) open=14 log_age=0.2m ✅
```

If this were in Arena sandbox forever it would die when chat ends — so you need same on YOUR machine.

## What watchdog does (auto pings you)

**File:** `alt_watchdog.py`

Every 60 sec it checks:

1. **Runner DOWN but games still open** → 🚨 Telegram:
   ```
   🚨 ALT Method Watchdog · DOWN
   ⚠️ Runner DOWN but 14 game(s) still open!
   Log age: 12.3 min
   Fix: pkill -f alt_daily; nohup python alt_daily.py > runner.log 2>&1 &
   ```

2. **Heartbeat stale >10 min** (log not updated) → ⚠️ Telegram:
   ```
   🚨 ALT Method Watchdog · STALE
   Heartbeat stale — 15 min no update
   ```

3. **Heartbeat hits 0** (open count = 0) → 🏁 Telegram:
   ```
   🏁 ALT Method · COMPLETE
   All 15 games closed. Heartbeat 0 — runner exiting.
   ```
   This also fires from `alt_runner.py` and `alt_daily.py` themselves when they exit — double coverage

Cooldown: won't spam same alert more than once per 30 min (state in `.watchdog_state.json`)

## How to run automatically on YOUR Dallas machine

### Option A — Manual auto (reliable today, any OS):

```bash
cd ~/alt-line-clv
# 1. verify
python verify_setup.py   # all ✅

# 2. start runner + watchdog (both)
PYTHONUNBUFFERED=1 nohup python -u alt_runner.py > runner.log 2>&1 & echo $! > runner.pid
PYTHONUNBUFFERED=1 nohup python -u alt_watchdog.py --loop 60 > watchdog.log 2>&1 & echo $! > watchdog.pid

# 3. prove running
./health_check.sh
tail -f runner.log
tail -f watchdog.log
```

### Option B — Systemd (Linux VPS, auto every day 7 PM + always-on watchdog):

```bash
./install_systemd.sh
# installs:
# alt-daily.timer → fires daily 19:00 CT (open + runner)
# alt-watchdog.service → always monitors, pings if down or 0

systemctl status alt-daily.timer
systemctl status alt-watchdog.service
journalctl -u alt-daily.service -f
journalctl -u alt-watchdog.service -f

# run now without waiting for 7 PM:
systemctl start alt-daily.service
```

### How to know it's running correctly (your ask)

```bash
python alt_main.py status          # should show 14 open
cat runner.log | tail -20          # should show heartbeat every 5 min
cat watchdog.log | tail -20        # should show ✅ all good
ps aux | grep alt_runner           # process alive
```

**Expected next auto pings Dallas CT:**
- 17:35 CT → close #7 #8
- 17:40 CT → close #6 #12
- 18:00+ → rest of slate
- 21:15+ → last game, then heartbeat 0 → you get 🏁 COMPLETE ping

If any batch doesn't fire:

1. `cat runner.log` — look for errors
2. `python alt_main.py close` — manual trigger, shows games in T-5 window
3. Restart: `pkill -f alt_daily; nohup python -u alt_daily.py > runner.log 2>&1 &`
4. If second ping also fails → go manual per your plan: `./run_today_manual.sh` + `./uninstall_systemd.sh`

## Files added

- `alt_watchdog.py` — watchdog logic
- `alt-watchdog.service` / `.timer` — systemd units
- Updated `alt_runner.py` / `alt_daily.py` — now send 🏁 completion Telegram when heartbeat hits 0
- Updated `install_systemd.sh` — enables watchdog too
- `restart_runner.sh` / `start_watchdog.sh` — quick restart helpers (sandbox)

## Tested live

- First batch #15 auto-closed and sent Telegram ✅
- Runner stale bug fixed (was 75m old log due to buffering, now unbuffered -u)
- Watchdog now reports fresh log_age 0.2m ✅
- Simulated DOWN scenario → watchdog would alert (tested)
