# ALT Method — Dallas CT Auto Setup (7 PM Daily)

**You live in Dallas, TX → America/Chicago timezone.**  
System is configured for that.

## What we just wired

You already have:

- `alt_main.py` — full system (open/close/rank/report/compare/test-telegram)
- `alt_runner.py` — T-5 polling runner (polls 30s, exits when slate closed)
- `telegram_creds.json` — bot @ProfitSniperHQBot → chat 5438406477, picks labeled **"ALT Method"**
- `data/alternate_model.db` — 15 MLB games frozen for 2026-07-24

New files added now:

- `alt_daily.py` — daily orchestrator (does open + runner in one process) **← RECOMMENDED for systemd**
- `alt-daily.service` — systemd service that runs alt_daily.py
- `alt-daily.timer` — triggers service daily at 19:00 local (CT)
- `alt-open.service` / `alt-runner.service` — optional split units
- `install_systemd.sh` — one-command installer
- `uninstall_systemd.sh` — one-command remover if it fails today
- `run_today_manual.sh` — manual fallback `nohup` runner for today

## Tonight's flow (automatic vs manual)

**Automatic (systemd):**
1. At 19:00 CT the timer fires `alt-daily.service`
2. `alt_daily.py` runs `open` for today (idempotent, safe to rerun)
3. Then loops: every 30s checks if any open game is 1-5 min from start
4. At T-5: pulls closing Pinnacle alternates, applies **THE KEY RULE: margin must drop**
5. Ranks by sharpness `(odds_move×0.4 + margin_drop×0.4 + promotion×0.2)`
6. Picks sharpest-only (rank-1 spread + rank-1 total) and sends Telegram as:
   `🎯 ALT Method · MLB`
7. Exits when all 15 games closed.

**Manual fallback (if systemd doesn't work today):**

On YOUR machine (not Arena sandbox):

```bash
cd /path/to/alt-line-clv
chmod +x run_today_manual.sh
./run_today_manual.sh
# or directly:
nohup python alt_daily.py > runner.log 2>&1 &
tail -f runner.log
```

In Arena sandbox we cannot keep a 4-hour daemon alive across sessions, so the nohup needs to run on your local machine / VPS where games start 15:10–21:15 CT.

## Install on your Linux server

```bash
# 1. copy this folder to your server
scp -r . user@server:~/alt-line-clv

# 2. ssh in
ssh user@server
cd ~/alt-line-clv

# 3. ensure deps
pip install requests

# 4. ensure creds exist (should already)
cat telegram_creds.json

# 5. install timer
chmod +x install_systemd.sh
./install_systemd.sh
# it will:
# - set timezone to America/Chicago if you approve
# - patch service files with your real user/path/python
# - enable alt-daily.timer

# 6. verify
systemctl list-timers alt-daily.timer
journalctl -u alt-daily.service -f
```

For today only, also:

```bash
systemctl start alt-daily.service   # run now, don't wait for 7 PM
```

If it fails:

```bash
chmod +x uninstall_systemd.sh
./uninstall_systemd.sh
# back to manual:
nohup python alt_daily.py > runner.log 2>&1 &
```

## Verification

```bash
python alt_main.py test-telegram   # should ping Telegram
python alt_main.py status          # 15 open for 2026-07-24
python alt_main.py rank 15         # Rockies example (will be empty until closed)
```

## Notes / Honest Caveats

- NHL/NFL return 403 in July (offseason) — handled, will auto-work when seasons start
- NBA/WNBA empty now — handled
- Frozen slate rule enforced: no late game additions after open
- Margin-drop rule is absolute: if margin rose or flat → line KILLED even if odds moved sharply
- 1u flat sizing until 50+ graded alternates
- Pinnacle reachable from sandbox; production should be fine
- systemd timer requires server timezone = America/Chicago to fire at true 7 PM Dallas time. If server is UTC, timer fires at 19:00 UTC (2 PM CT) — so set tz correctly.

## Today's games CT (game # in DB)

15:10 Rockies@Brewers #15 · 17:40 Cubs@Pirates #7, Royals@Tigers #8 · 17:45 Yankees@Phils #6, Dbacks@Nats #12 · 18:05 Braves@Orioles #9 · 18:10 Guardians@Rays #5, Padres@Marlins #10, Dodgers@Mets #11 · 18:15 BlueJays@RedSox #3 · 18:40 Astros@WhiteSox #2 · 19:05 Mariners@Rangers #1 · 19:10 A's@Twins #4 · 19:15 Reds@Cards #13 · 21:15 Angels@Giants #14
