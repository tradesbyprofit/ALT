# ALT Method — First Batch Report — 2026-07-24 Dallas CT

**Executed:** 2026-07-24 15:07 CT (T-3m window)
**Slates:** 15 frozen → 1 closed, 14 open
**Runner:** PID 1410 active, polling 30s, next batch 17:40 CT

## Game #15 — Colorado Rockies @ Milwaukee Brewers — 15:10 CT — CLOSED

**Pinnacle board:** 7 spreads + 7 totals = 14 lines

### THE KEY RULE in action (margin must drop):
- Main spread -1.5 (-118 → -125) **KILLED** — margin rose 2.44% → 2.50%
- This is exactly why we track alts — main got steamed but juiced, alts compressed

### SPREADS ranked:
1. **⭐ SHARPEST — HOME -2.5 (+125)** — Milwaukee -2.5
   - moved +131 → +125 (6¢ sharper)
   - margin 3.6% → 3.5% ↓0.1 — ALIVE
   - sharpness 0.700
2. HOME -3.0 (+162) — 8¢ move, margin drop 0.10
3. HOME -1.0 (-202) — 8¢ move
4. HOME -2.0 (+101) — 6¢ move
5. KILLED: -1.5 main — margin rose
6. KILLED: +1.0, +1.5 — margin flat/rose

### TOTALS:
- ALL KILLED — no live alternates
  - 7.0, 7.5, 8.0 killed for margin rose
  - 8.5 (main), 9.0, 9.5, 10.0 killed for move <5¢ min

### Telegram alert sent:
```
🎯 ALT Method · MLB
Colorado Rockies v Milwaukee Brewers
⏱ closing snapshot · 15:10 CT

SPREAD sharpest: HOME -2.5 (+125)
  moved +131 → +125 (6¢ sharper)
  margin 3.6% → 3.5% ↓0.1
```
Label: **ALT Method** (sharpest-only mode)
No total pick for this game — correct per rule.

## Next batches Dallas CT

- 17:40 #7 Cubs@Pirates, #8 Royals@Tigers — T-5 at 17:35 CT (~2.5h)
- 17:45 #6 Yankees@Phils, #12 Dbacks@Nats
- 18:05 #9 Braves@Orioles
- 18:10 #5 Guardians@Rays, #10 Padres@Marlins, #11 Dodgers@Mets
- 18:15 #3 BlueJays@RedSox
- 18:40 #2 Astros@WhiteSox
- 19:05 #1 Mariners@Rangers
- 19:10 #4 A's@Twins
- 19:15 #13 Reds@Cards
- 21:15 #14 Angels@Giants

Runner polling: `tail -f runner.log`

## Commands to grade tonight

After games final:

```bash
python alt_main.py report 2026-07-24
python alt_main.py compare 2026-07-24
```

This will compare sharpest-alt record vs main-line record → alt-edge.

## Files updated

- data/alternate_model.db — 1 closed, 14 open
- runner.log — live heartbeat
- telegram_creds.json — bot active

Runner will exit automatically when all 14 remaining close. For reliable overnight, run on your own machine:
`nohup python alt_runner.py > runner.log 2>&1 &`
or `systemctl start alt-daily.service`

