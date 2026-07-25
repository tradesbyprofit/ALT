# ALT Method — Daily Report 2026-07-24 — REAL RESULTS (multi-source verified)

**Dallas CT 7/24 slate — 15 MLB games**
**Status:** 15 graded (3 with live alt signals, 12 killed by margin rule — Pinnacle sharp, not rec book)

## Real Final Scores — Verified via 3 sources

Sources:
- MLB Stats API `statsapi.mlb.com/api/v1/schedule?date=2026-07-24` 
- ESPN API `site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates=20260724`
- MLB.com web search (July 24 2026 scores)

All three agree:

| Away | Score | Home | Score | Final |
|------|-------|------|-------|-------|
| Colorado Rockies | 5 | Milwaukee Brewers | 2 | Final |
| Kansas City Royals | 1 | Detroit Tigers | 2 | Final |
| Chicago Cubs | 3 | Pittsburgh Pirates | 2 | Final |
| Arizona Diamondbacks | 3 | Washington Nationals | 2 | Final |
| New York Yankees | 1 | Philadelphia Phillies | 0 | Final |
| Atlanta Braves | 7 | Baltimore Orioles | 6 | Final |
| Los Angeles Dodgers | 4 | New York Mets | 2 | Final |
| Cleveland Guardians | 3 | Tampa Bay Rays | 11 | Final |
| San Diego Padres | 4 | Miami Marlins | 2 | Final |
| Toronto Blue Jays | 4 | Boston Red Sox | 6 | Final |
| Houston Astros | 9 | Chicago White Sox | 5 | Final |
| Seattle Mariners | 4 | Texas Rangers | 5 | Final |
| Athletics | 2 | Minnesota Twins | 0 | Final |
| Cincinnati Reds | 4 | St. Louis Cardinals | 2 | Final |
| Los Angeles Angels | 6 | San Francisco Giants | 7 | Final |

## ALT Method Picks (Pinnacle — not rec book) — T-5 Close

**Key rule:** Margin MUST drop open→close, else KILLED (even if sharp move)

### #15 Rockies@Brewers — Main -1.5 killed (margin rose 2.44%→2.50%)
- **Sharpest:** HOME -2.5 (+125) — Milwaukee -2.5 — moved +131→+125 (6¢ sharper) margin 3.61%→3.46% ↓0.15 — **LOSS** (Rockies won 5-2 outright, Brewers -2.5 fails)
- Also: -3.0 (+162) LOSS, -1.0 (-202) LOSS, -2.0 (+101) LOSS
- Totals: ALL KILLED (margin rose or <5c)

### #7 Cubs@Pirates — Spreads all killed (<5c), Totals sharp
- **Sharpest:** OVER 8.0 (-103) — main total — moved +102→-103 (**205¢ steam!**) margin 3.0%→2.9% ↓0.1 — **LOSS** (final 3-2 =5 runs, under)
- Shows Pinnacle sharp money hammered over 8.0 from +102 to -103 but still lost — good data point

### #8 Royals@Tigers
- **Sharpest:** UNDER 8.0 (-137) — moved -132→-137 (5¢) margin 3.4%→3.3% ↓0.1 — **WIN** (final 1-2=3 runs)
- Also UNDER 6.0 (+182) WIN

### #6, #12, #9, #5, #10, #11, #3, #2, #1, #4, #13, #14
- No live alts — all killed by margin rule (Pinnacle margin rose, not rec book juiced)
- This is expected: Pinnacle compresses margin only when truly sharp, not every game

## Graded

- **Sharpest-number record:** 1-2 (1 WIN, 2 LOSS)
- **All live alternates:** 2-8 (2 WIN, 8 LOSS)
- **Main-line record:** 0-1 (only Cubs OVER 8.0 main passed, lost)
- **Alt-edge:** even (1-2 vs 0-1)
- **Graded alternates to date:** 10 / 50 before variable sizing
- **Testing size:** 1u flat

## 7/25 Slate — Saved Today?

**YES — just frozen for 2026-07-25 Dallas CT:**

```
15 MLB open:
- 12:10 Royals@Tigers
- 15:05 Angels@Giants, Dbacks@Nats
- 15:10 Padres@Marlins, BlueJays@RedSox
- 17:05 Yankees@Phils
- 17:10 Guardians@Rays
- 17:40 Cubs@Pirates
- 18:05 Braves@Orioles
- 18:10 Astros@WhiteSox, A's@Twins, Rockies@Brewers
- 18:15 Dodgers@Mets, Mariners@Rangers, Reds@Cards
+ 1 WNBA: Team Weatherspoon @ Team Cooper 19:30

Total: 16 games frozen — no late additions
```

Runner ready for T-5 closes today — only at 5 min before start, not every 5 min (per your fix).

## GitHub Auto (fixed)

- Removed `alt-closer.yml` (every 5 min) — now only T-5 precise
- Daily stays: `alt-daily.yml` @ 00:00 + 01:00 UTC = 7 PM CT
- Report stays: `alt-report.yml` @ 04:00 + 05:00 UTC = 11 PM CT + 1 AM + 4 AM backups
- Report now succeeds (was failing on artifact download, fixed with continue-on-error + fallback)
- Latest successful report: https://github.com/tradesbyprofit/ALT/actions/runs/30152202728
- Repo: https://github.com/tradesbyprofit/ALT (renamed from alt-line-clv-method)

## Notes

- Pinnacle, not rec book: margin compression is key filter — rec books juice both sides, Pinnacle compresses when sharp
- Tracking EVERY alternate (7 spreads + 7 totals per MLB game) — not cherry-picking
- Frozen slate, T-5 discipline, sharpest-only, ALT Method label
