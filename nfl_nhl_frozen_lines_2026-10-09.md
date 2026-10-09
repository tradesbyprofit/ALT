# NFL & NHL Opening Alternate Lines — Slate 2026-10-09 (America/Chicago)

**Pulled live from Pinnacle guest API via GitHub Actions, 2026-10-09 ~12:56 PM CT.**

> Main line marked with ★. Odds are American at opening-pull time.
> NFL: league_id 889 (813 matchups in-season). NHL: league_id 1456 (279 matchups in-season).
> These are the CORRECT league IDs — the repo had stale ones (NFL 676, NHL 579) left over
> from when the leagues were last mapped; Pinnacle's internal taxonomy changed sport_ids too
> (Football is now sport_id 15, Hockey is sport_id 19). Fixed in alt_main.py this session.

## NFL — 0 games on 2026-10-09

No NFL games today. Week 5's Thursday night game (Buccaneers @ Cowboys) already played
10/8. Next NFL games are Sunday 10/11. This is correct/expected, not a pull failure —
confirmed independently against the public NFL schedule.

## NHL — 4 games captured

---

## Seattle Kraken @ Detroit Red Wings  ·  18:07  ·  #1

Main: spread -1.5 · total 6.0

**Moneyline**

| home | away |
|---:|---:|
| -141 | +127 |

**Spreads** (line = home handicap)

| line | home | away | margin | |
|---:|---:|---:|---:|:--:|
| -2.5 | +297 | -382 | 4.44% |  |
| -1.5 | +177 | -204 | 3.21% | ★ |
| +1.5 | -383 | +297 | 4.48% |  |
| +2.5 | -702 | +489 | 4.51% |  |

**Totals**

| line | over | under | margin | |
|---:|---:|---:|---:|:--:|
| 5.0 | -282 | +233 | 3.85% |  |
| 5.5 | -133 | +114 | 3.81% |  |
| 6.0 | -106 | -106 | 2.91% | ★ |
| 6.5 | +114 | -134 | 3.99% |  |
| 7.0 | +203 | -243 | 3.85% |  |
| 8.5 | +410 | -532 | 3.79% |  |

## New York Rangers @ Washington Capitals  ·  18:07  ·  #2

Main: spread -1.5 · total 5.5

**Moneyline**

| home | away |
|---:|---:|
| -134 | +121 |

**Spreads** (line = home handicap)

| line | home | away | margin | |
|---:|---:|---:|---:|:--:|
| -2.5 | +319 | -416 | 4.49% |  |
| -1.5 | +192 | -222 | 3.19% | ★ |
| +1.5 | -372 | +290 | 4.45% |  |
| +2.5 | -709 | +493 | 4.50% |  |

**Totals**

| line | over | under | margin | |
|---:|---:|---:|---:|:--:|
| 4.5 | -358 | +289 | 3.87% |  |
| 5.0 | -243 | +203 | 3.85% |  |
| 5.5 | -118 | +105 | 2.91% | ★ |
| 6.0 | +105 | -122 | 3.74% |  |
| 6.5 | +129 | -151 | 3.83% |  |
| 8.5 | +469 | -623 | 3.74% |  |

## Pittsburgh Penguins @ Columbus Blue Jackets  ·  18:07  ·  #3

Main: spread -1.5 · total 6.5

**Moneyline**

| home | away |
|---:|---:|
| -113 | +102 |

**Spreads** (line = home handicap)

| line | home | away | margin | |
|---:|---:|---:|---:|:--:|
| -2.5 | +353 | -469 | 4.50% |  |
| -1.5 | +217 | -253 | 3.22% | ★ |
| +1.5 | -297 | +238 | 4.40% |  |
| +2.5 | -530 | +390 | 4.54% |  |

**Totals**

| line | over | under | margin | |
|---:|---:|---:|---:|:--:|
| 5.5 | -175 | +149 | 3.80% |  |
| 6.0 | -147 | +126 | 3.76% |  |
| 6.5 | -115 | +102 | 2.99% | ★ |
| 7.0 | +148 | -174 | 3.83% |  |
| 7.5 | +214 | -257 | 3.84% |  |

## Anaheim Ducks @ Winnipeg Jets  ·  19:07  ·  #4

Main: spread -1.5 · total 6.5

**Moneyline**

| home | away |
|---:|---:|
| -121 | +110 |

**Spreads** (line = home handicap)

| line | home | away | margin | |
|---:|---:|---:|---:|:--:|
| -2.5 | +340 | -449 | 4.51% |  |
| -1.5 | +208 | -242 | 3.23% | ★ |
| +1.5 | -319 | +254 | 4.38% |  |
| +2.5 | -595 | +428 | 4.55% |  |

**Totals**

| line | over | under | margin | |
|---:|---:|---:|---:|:--:|
| 5.5 | -152 | +130 | 3.80% |  |
| 6.0 | -124 | +106 | 3.90% |  |
| 6.5 | +104 | -116 | 2.72% | ★ |
| 7.0 | +176 | -209 | 3.87% |  |
| 7.5 | +242 | -295 | 3.92% |  |

---

*Note: Pinnacle's board also listed a 4-game NHL "Team Total / correlated" special
(Away Goals @ Home Goals, total 25.5) — excluded here since it's not a single-game
matchup, consistent with how `alt_main.py`'s production `open` command filters specials.*
