# GitHub Auto Setup — DONE ✅

**Repo:** https://github.com/tradesbyprofit/alt-line-clv-method (private)
**User:** tradesbyprofit
**Created:** 2026-07-24

## What was done

1. Created private repo `alt-line-clv-method` via API
2. Pushed all ALT Method files (24 files, 3270 lines) with .gitignore that EXCLUDES:
   - telegram_creds.json (SECRET)
   - data/*.db, *.log, *.pid, .watchdog_state.json
3. Created GitHub Actions workflows:
   - `.github/workflows/alt-daily.yml` — Daily 7 PM CT auto (00:00 UTC + 01:00 UTC crons to cover DST)
     - Runs `alt_daily.py` (open + T-5 runner up to 6h)
     - Sends Telegram as ALT Method at T-5
     - Sends 🏁 COMPLETE ping when heartbeat hits 0 (all closed)
     - Uploads DB + logs as artifact
   - `.github/workflows/alt-closer.yml` — Every 5 min during 3PM-11PM CT window (20:00-04:00 UTC)
     - Safety net: runs `close` if daily job missed
4. Added GitHub Secrets via encrypted API:
   - TG_BOT_TOKEN → your bot token
   - TG_CHAT_ID → 5438406477
   - Verified: 2 secrets active
5. Triggered first run manually — currently in_progress:
   - https://github.com/tradesbyprofit/alt-line-clv-method/actions/runs/30130611405
   - Will handle remaining 14 games (next T-5 17:35 CT)

## How auto works now (Dallas CT)

- **19:00 CT daily:** GitHub Actions wakes up, runs open freeze, then loops T-5 polls
- **T-5 window:** When game 1-5 min from start, pulls Pinnacle, applies margin-drop rule, ranks sharpest, pings Telegram
- **Watchdog built-in:**
  - Runner DOWN but games open → 🚨 DOWN ping (via alt_watchdog.py if you run it, plus Actions closer as backup)
  - Heartbeat 0 (all closed) → 🏁 COMPLETE ping (from alt_runner.py + alt_daily.py)
- **Every 5 min closer:** Backup workflow ensures no missed closes if main job dies

## How to know it's running correctly

- Go to Actions tab: https://github.com/tradesbyprofit/alt-line-clv-method/actions
- You should see "ALT Method Daily" in_progress now
- Click run → see logs: Dallas time, verification, Telegram ON, then heartbeat logs
- Check Telegram — you already got first batch #15, next at 17:35 CT
- Artifacts after run contain DB + logs

## To manually trigger

Actions → ALT Method Daily → Run workflow → enter slate date (or leave blank for today)

## Secrets management

- Never commit telegram_creds.json — it's gitignored
- In CI, it uses TG_BOT_TOKEN / TG_CHAT_ID env vars from GitHub Secrets
- To rotate token: Repo Settings → Secrets → update

## Local fallback still works

If GitHub Actions fails (first run test), you still have:
```bash
./verify_setup.py
PYTHONUNBUFFERED=1 nohup python -u alt_daily.py > runner.log 2>&1 &
PYTHONUNBUFFERED=1 nohup python -u alt_watchdog.py --loop 60 > watchdog.log 2>&1 &
```

## Security

- Repo is private — only you can see it
- Token file deleted from sandbox after use
- Consider rotating GitHub PAT after setup (Settings → Developer settings → Tokens)
- Telegram token is in GitHub Secrets encrypted, not in code

## Next steps

1. Watch Actions run live for next 2h till 17:35 CT batch
2. Wait for Telegram ping at 17:35 CT — that's proof auto works
3. If first GitHub ping fails, check Actions logs → readjust → test on next batch 17:40 CT
4. If second fails → go manual per your plan

