# ALT Method — Alternate-Line CLV Tracker

Tracks **EVERY** Pinnacle alternate spread/total line (not just main) to find which specific numbers sharp money targeted. Does playing the sharpest alternate number outperform main line?

**Dallas CT 7 PM daily auto** via GitHub Actions + Telegram pings labeled **ALT Method**.

## Core Question
Does playing the sharpest alternate number (by odds movement + margin compression) outperform playing the main line over time?

## Key Rule (no exceptions)
**Margin MUST drop open→close for a line to be ALIVE.** If margin rose or flat → KILLED. Even if odds moved sharply.

## System

- **Data:** Pinnacle public guest API (`guest.api.arcadia.pinnacle.com`) — no login, American odds
- **Frozen slate:** No late game additions after 7 PM capture
- **T-5 window:** Closing pull 1-5 min before start (sharpest action)
- **Ranking:** `(odds_move_norm × 0.4) + (margin_drop_norm × 0.4) + (promotion_bonus × 0.2)`
- **Alert format:** `🎯 ALT Method · {LEAGUE}` — sharpest-only (rank-1 spread + rank-1 total)
- **Grading:** ESPN scoreboard API, compares alt-edge vs main-line
- **Testing:** 1u flat per play until 50+ graded alternates

## Commands

```bash
python alt_main.py open [YYYY-MM-DD]     # 7 PM freeze all alts
python alt_main.py close [game_id]       # T-5 close pull
python alt_main.py rank [game_id]        # ranked sharpest alts
python alt_main.py report [YYYY-MM-DD]   # grade vs results
python alt_main.py compare [YYYY-MM-DD]  # alt vs main line perf
python alt_main.py status                # slate overview
python alt_main.py test-telegram         # test bot
```

## GitHub Actions Auto (Dallas CT)

This repo runs automatically via GitHub Actions:

- **Daily 7 PM CT:** `alt_daily.py` does open + T-5 runner loop (up to 6h, pings Telegram)
- **Manual:** Actions → Run workflow → enter slate date
- **Secrets needed:** Add in Repo Settings → Secrets and variables → Actions:
  - `TG_BOT_TOKEN` = your @ProfitSniperHQBot token
  - `TG_CHAT_ID` = your chat id (5438406477)
- Workflow file: `.github/workflows/alt-daily.yml`
- Cron: `0 0 * * *` UTC = 7 PM CDT (summer), `0 1 * * *` = 7 PM CST (winter) — covers DST

### Setup GitHub Secrets:

1. Go to https://github.com/tradesbyprofit/alt-line-clv-method/settings/secrets/actions
2. New repository secret:
   - Name: `TG_BOT_TOKEN`, Value: `8824554066:AAE...` (your bot token)
   - Name: `TG_CHAT_ID`, Value: `5438406477`
3. Rerun workflow — it will auto-ping Telegram at T-5

## Local Dallas Setup (systemd)

For VPS in Dallas timezone:

```bash
./install_systemd.sh
systemctl list-timers alt-daily.timer
journalctl -u alt-daily.service -f

# watchdog pings if runner dies or heartbeat hits 0
./verify_setup.py
PYTHONUNBUFFERED=1 nohup python -u alt_watchdog.py --loop 60 > watchdog.log 2>&1 &
```

## Files

- `alt_main.py` — core system (1623 lines)
- `alt_daily.py` — daily orchestrator (open + runner)
- `alt_runner.py` — T-5 polling runner
- `alt_watchdog.py` — monitors runner, pings if down or heartbeat 0
- `alt-daily.service/.timer`, `alt-watchdog.service` — systemd units
- `verify_setup.py`, `health_check.sh` — health checks
- `data/alternate_model.db` — SQLite (gitignored, lives in Actions artifacts)
- `telegram_creds.json` — SECRET, gitignored, use env vars in CI

## Tonight's Flow

15 frozen → close at T-5 → Telegram `🎯 ALT Method` → grade vs ESPN → compare alt-edge

## Watchdog

- Runner DOWN but games open → 🚨 DOWN ping
- Heartbeat stale >10m → ⚠️ STALE ping  
- Heartbeat hits 0 (all closed) → 🏁 COMPLETE ping

## Disclaimer

1u flat during testing. System tracks every alternate — don't cherry-pick. Complements main method (main = WHICH SIDE, alt = WHICH NUMBER).

Built for Dallas CT (America/Chicago).
