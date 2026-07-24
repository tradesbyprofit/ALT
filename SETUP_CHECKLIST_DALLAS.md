# Dallas Setup Checklist — Prove Auto is Running Correctly

**Goal:** Run automatically, verify first ping works, if not readjust and test next ping, if that fails go manual. Dallas CT.

## You are here
- First batch JUST worked: #15 Rockies@Brewers at 15:10 CT closed, Telegram sent Milwaukee -2.5 (+125) as ALT Method — proves core logic + Telegram works
- 14 games remain: next batch 17:40 CT (Cubs@Pirates, Royals@Tigers) — T-5 at **17:35 CT**

## Step 1 — Copy to your machine (once)

Arena sandbox can't keep 4hr daemon. Must run on YOUR server/laptop/VPS in Dallas.

```bash
# On your Mac/Linux:
scp -r /home/user/* your_server:~/alt-line-clv/
# or download zip from Arena

ssh your_server
cd ~/alt-line-clv
pip install requests
```

## Step 2 — Verify setup (2 min)

```bash
chmod +x verify_setup.py health_check.sh
python verify_setup.py
# Expected: all ✅
# - 15 games frozen → 1 closed, 14 open
# - Telegram enabled chat 5438406477
# - Pinnacle reachable
# - Dallas time correct
```

If any ❌, fix:
- ❌ requests missing → `pip install requests`
- ❌ telegram not enabled → check `telegram_creds.json` exists (secret file, don't commit)
- ❌ Pinnacle 403 on NHL/NFL → normal in July offseason, ignore
- ❌ timezone not America/Chicago → `sudo timedatectl set-timezone America/Chicago`

## Step 3 — Test Telegram (10 sec)

```bash
python alt_main.py test-telegram
# Check phone — should get:
# 🎯 ALT Method · CONNECTION TEST
```

If no ping → token/chat wrong. Re-check telegram_creds.json.

## Step 4 — Choose auto mode

**Option A — Manual auto (works everywhere, Mac + Linux, most reliable for today):**

```bash
nohup python alt_daily.py > runner.log 2>&1 &
echo $! > runner.pid
tail -f runner.log
# you should see:
# [15:08:50] 🎯 ALT Method runner started
# [15:08:50] telegram ON
# [15:1x:xx] 💓 heartbeat — 14 open · next Cubs @ Pirates in 138 min
```

**Option B — Systemd daily 7 PM (Linux VPS, fires automatically daily):**

```bash
chmod +x install_systemd.sh
./install_systemd.sh
# checks timezone, patches service files, enables timer

systemctl list-timers alt-daily.timer
# should show NEXT = today 19:00

systemctl status alt-daily.timer
journalctl -u alt-daily.service -f   # live logs

# to run NOW without waiting for 7 PM:
systemctl start alt-daily.service
```

## Step 5 — Prove it's running correctly (what you asked)

Run health check:

```bash
./health_check.sh
```

You want to see:

- ✅ runner.pid running
- ✅ runner.log with heartbeat every 5 min
- ✅ `python alt_main.py status` shows 1 closed, 14 open
- ✅ Next T-5 time calculated correctly (Dallas CT)

Example good output:

```
✅ runner PID 1410 running
[15:08:50] 🎯 ALT Method runner started
[15:13:50] 💓 heartbeat — 14 open · next Cubs @ Pirates in 133 min
```

If bad:

- No process → start it again
- No heartbeat → check `runner.log` for errors (Pinnacle fetch, telegram)
- Timer not active → `systemctl enable --now alt-daily.timer`

## Step 6 — Wait for next ping (17:35 CT)

Don't tail for 2.5 hours — just wait for Telegram.

Expected at 17:35 CT Dallas:

- #7 Cubs@Pirates + #8 Royals@Tigers close
- If any alt passes margin-drop + 5c move, you get:
  ```
  🎯 ALT Method · MLB
  Chicago Cubs v Pittsburgh Pirates
  ⏱ closing snapshot · 17:40 CT

  SPREAD sharpest: ...
  ```

## Step 7 — If first ping fails (your plan)

**If 17:35 batch fails:**

1. Check logs immediately:
   ```bash
   cat runner.log | tail -30
   python alt_main.py status
   python alt_main.py close   # manual trigger — shows if games were in window
   ```

2. Common fixes:
   - Telegram silent? `python alt_main.py test-telegram` → if fails, token expired
   - Pinnacle empty? `python alt_main.py open 2026-07-24` → re-freeze (idempotent)
   - Margin kills all? That's NORMAL — not a failure, just no edge that game (like totals in first batch)
   - Runner died? `cat runner.log`, restart `nohup python alt_daily.py > runner.log 2>&1 &`

3. Readjust and test on **next ping** (17:40 CT Yankees@Phils etc.):
   ```bash
   # restart clean:
   pkill -f alt_daily
   nohup python alt_daily.py > runner.log 2>&1 &
   ```

## Step 8 — If second ping fails → go manual

Per your plan, go manual:

```bash
chmod +x uninstall_systemd.sh
./uninstall_systemd.sh

# manual loop:
while true; do
  python alt_main.py close
  sleep 30
done

# or for today only:
./run_today_manual.sh
```

Manual still sends Telegram same way.

## Tonight grading

After all games (after 21:15 CT last game):

```bash
python alt_main.py report 2026-07-24
python alt_main.py compare 2026-07-24
# shows alt-edge vs main line
```

## What you have now in this sandbox

- PID 1410 running, 1 closed, 14 open, next T-5 17:35 CT
- Telegram proven working (first batch sent)
- All verification scripts ready to copy to your Dallas machine
