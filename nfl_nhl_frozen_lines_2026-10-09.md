# NFL & NHL Opening Alternate Lines — Slate 2026-10-09 (America/Chicago)

**Pulled live from Pinnacle guest API via GitHub Actions, 2026-10-09 ~1:13 PM CT.**
**Now includes Pinnacle's `maxRiskStake` bet limit per line** (pulled from the raw
`limits` array on each market row — this field existed in the API all along but
`alt_main.py` was discarding it; now captured and stored in `lines.limit_open` /
`lines.limit_close` for every future open/close pull, production-wide).

> Main line marked with ★. Odds are American at opening-pull time.
> NFL: league_id 889 (813 matchups in-season). NHL: league_id 1456 (279 matchups in-season).
> These are the CORRECT league IDs — the repo had stale ones (NFL 676, NHL 579) left over
> from when the leagues were last mapped; Pinnacle's internal sport taxonomy changed too
> (Football is now sport_id 15, Hockey is sport_id 19). Fixed in alt_main.py this session.

**Why limits matter (per your ask):** Pinnacle sizes its max bet per line based on how
comfortable it is taking action there. A thin limit on an alternate = Pinnacle doesn't
want exposure there (less reliable/liquid number). A limit that gets RAISED between
open and close on a specific alt = Pinnacle got comfortable, usually because sharp
money already hit it and it's been "tested." Combined with the existing
odds-move + margin-drop signals, the limit gives you a third, independent read on
which number the book itself trusts — reading the whole market (every alt, every
limit) instead of just the main line is exactly what lets you compare opportunities
across games and only pull the trigger when multiple signals stack, instead of
forcing a play off one data point.

**Reality check on today's data:** every NHL alt spread/total tonight carries the same
flat $3,750 limit, with only the moneyline sitting higher at $5,000. So on this slate,
the limit field isn't discriminating between alternates yet — it's flat. That's normal
for an opening snapshot; limits are more likely to diverge by closing time (T-5) as
real money moves specific numbers. The field is now wired into every future close pull,
so the open→close delta will be visible going forward, including tonight if the T-5
runner executes near game time.

## NFL — 0 games on 2026-10-09

No NFL games today. Week 5's Thursday night game (Buccaneers @ Cowboys) already played
10/8. Next NFL games are Sunday 10/11. Confirmed against the public NFL schedule —
not a pull failure.

## NHL — 4 games captured

---

## Seattle Kraken @ Detroit Red Wings  ·  18:07  ·  #1

Main: spread -1.5 · total 6.0

**Moneyline**

| home | away | max limit |
|---:|---:|---:|
| -141 | +127 | $5,000 |

**Spreads** (line = home handicap)

| line | home | away | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| -2.5 | +297 | -382 | 4.44% | $3,750 |  |
| -1.5 | +177 | -204 | 3.21% | $3,750 | ★ |
| +1.5 | -383 | +297 | 4.48% | $3,750 |  |
| +2.5 | -702 | +489 | 4.51% | $3,750 |  |

**Totals**

| line | over | under | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| 5.0 | -282 | +233 | 3.85% | $3,750 |  |
| 5.5 | -133 | +114 | 3.81% | $3,750 |  |
| 6.0 | -106 | -106 | 2.91% | $3,750 | ★ |
| 6.5 | +114 | -134 | 3.99% | $3,750 |  |
| 7.0 | +203 | -243 | 3.85% | $3,750 |  |
| 8.5 | +410 | -532 | 3.79% | $3,750 |  |

## New York Rangers @ Washington Capitals  ·  18:07  ·  #2

Main: spread -1.5 · total 5.5

**Moneyline**

| home | away | max limit |
|---:|---:|---:|
| -134 | +121 | $5,000 |

**Spreads** (line = home handicap)

| line | home | away | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| -2.5 | +319 | -416 | 4.49% | $3,750 |  |
| -1.5 | +192 | -222 | 3.19% | $3,750 | ★ |
| +1.5 | -372 | +290 | 4.45% | $3,750 |  |
| +2.5 | -709 | +493 | 4.50% | $3,750 |  |

**Totals**

| line | over | under | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| 4.5 | -358 | +289 | 3.87% | $3,750 |  |
| 5.0 | -243 | +203 | 3.85% | $3,750 |  |
| 5.5 | -118 | +105 | 2.91% | $3,750 | ★ |
| 6.0 | +105 | -122 | 3.74% | $3,750 |  |
| 6.5 | +129 | -151 | 3.83% | $3,750 |  |
| 8.5 | +469 | -623 | 3.74% | $3,750 |  |

## Pittsburgh Penguins @ Columbus Blue Jackets  ·  18:07  ·  #3

Main: spread -1.5 · total 6.5

**Moneyline**

| home | away | max limit |
|---:|---:|---:|
| -113 | +102 | $5,000 |

**Spreads** (line = home handicap)

| line | home | away | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| -2.5 | +353 | -469 | 4.50% | $3,750 |  |
| -1.5 | +217 | -253 | 3.22% | $3,750 | ★ |
| +1.5 | -297 | +238 | 4.40% | $3,750 |  |
| +2.5 | -530 | +390 | 4.54% | $3,750 |  |

**Totals**

| line | over | under | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| 5.5 | -175 | +149 | 3.80% | $3,750 |  |
| 6.0 | -147 | +126 | 3.76% | $3,750 |  |
| 6.5 | -115 | +102 | 2.99% | $3,750 | ★ |
| 7.0 | +148 | -174 | 3.83% | $3,750 |  |
| 7.5 | +214 | -257 | 3.84% | $3,750 |  |

## Anaheim Ducks @ Winnipeg Jets  ·  19:07  ·  #4

Main: spread -1.5 · total 6.5

**Moneyline**

| home | away | max limit |
|---:|---:|---:|
| -121 | +110 | $5,000 |

**Spreads** (line = home handicap)

| line | home | away | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| -2.5 | +340 | -449 | 4.51% | $3,750 |  |
| -1.5 | +208 | -242 | 3.23% | $3,750 | ★ |
| +1.5 | -319 | +254 | 4.38% | $3,750 |  |
| +2.5 | -595 | +428 | 4.55% | $3,750 |  |

**Totals**

| line | over | under | margin | max limit | |
|---:|---:|---:|---:|---:|:--:|
| 5.5 | -152 | +130 | 3.80% | $3,750 |  |
| 6.0 | -124 | +106 | 3.90% | $3,750 |  |
| 6.5 | +104 | -116 | 2.72% | $3,750 | ★ |
| 7.0 | +176 | -209 | 3.87% | $3,750 |  |
| 7.5 | +242 | -295 | 3.92% | $3,750 |  |

---

## My read across the whole board (skips encouraged — nothing forced)

Looking at all 4 games side by side instead of one line at a time:

- **Margin is nearly identical across every alt (2.7%–4.5%) on all 4 games** — Pinnacle's
  juice structure tonight is templated, not game-specific. That's a flat market, not a
  divergent one.
- **Limits are flat too** ($3,750 every alt, $5,000 every ML) — no line on any of these
  4 games is getting treated as "riskier" than another by the book right now. No
  standout limit signal at opening.
- **No odds-move or margin-drop signal exists yet** because this is the OPENING pull —
  the whole point of the ALT method is comparing open vs T-5 close. Right now we only
  have one snapshot, so there's nothing to rank or grade yet.

**Bottom line: this is a skip, not a pick.** Four flat, templated markets with zero
divergence and no closing data yet isn't "a good ass pick" by the system's own rule
(margin must actually move, odds must actually move). The real signal only shows up
once the T-5 close pull runs tonight (~18:02–19:02 CT) and we can compare open→close
on all 4 games together. Rerun `alt_main.py close` or let the daily runner hit T-5
tonight, and I'll pull the same side-by-side comparison with real movement data.
