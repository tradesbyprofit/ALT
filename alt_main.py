#!/usr/bin/env python3
"""
Alternate-Line CLV Method — alt_main.py
=======================================

Tracks EVERY alternate spread and total line on Pinnacle's board (not just the
main line) to find which SPECIFIC numbers sharp money targeted.

Core question being tested:
    Does playing the sharpest ALTERNATE number (by odds movement + margin
    compression) outperform playing the main line over time?

Commands:
    python alt_main.py open [YYYY-MM-DD]     capture all alternates for a slate
    python alt_main.py close [game_id]       T-5 closing pull for games 1-5 min out
    python alt_main.py rank [game_id]        ranked sharpest alternates for game(s)
    python alt_main.py report [YYYY-MM-DD]   grade alt signals vs actual results
    python alt_main.py compare [YYYY-MM-DD]  alt-line vs main-line performance
    python alt_main.py status                show slate overview
    python alt_main.py config                print active configuration

Data source: Pinnacle public guest JSON API (no login).
Grading:     ESPN public scoreboard API.
Storage:     SQLite at data/alternate_model.db
"""

from __future__ import annotations

import html
import json
import sqlite3
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError:  # pragma: no cover
    print("ERROR: `requests` is required. Install with: pip install requests")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    "mode": "live",
    "timezone": "America/Chicago",
    "sports": ["mlb", "nba", "nhl", "nfl", "wnba"],
    "league_ids": {
        "mlb": 246,
        "nba": 487,
        "wnba": 578,
        "nhl": 579,
        "nfl": 676,
    },
    "sport_ids": {
        "mlb": 3,
        "nba": 4,
        "wnba": 4,
        "nhl": 5,
        "nfl": 6,
    },
    "pinnacle": {
        "base": "https://guest.api.arcadia.pinnacle.com",
        "version": "0.1",
        "api_key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R",
    },
    "espn": {
        "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        "wnba": "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
        "nhl": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
        "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    },
    "capture": {
        "opening_hour": 19,          # 7 PM pull (operational guidance)
        "closing_window_min": 1,     # T-5 window: 1..5 minutes before start
        "closing_window_max": 5,
        "frozen_slate": True,        # no late additions
    },
    "analysis": {
        "min_odds_move_cents": 5,    # minimum movement to qualify (5 cents American)
        "margin_must_drop": True,    # THE KEY RULE
        "margin_epsilon": 0.01,      # ignore sub-noise margin ticks (pct points)
    },
    "ranking": {
        "odds_weight": 0.4,
        "margin_weight": 0.4,
        "promotion_weight": 0.2,
    },
    "testing": {
        "flat_units": 1.0,           # 1u flat during testing
        "variable_sizing_after": 50, # graded alternates before variable sizing
    },
    "alerts": {
        "telegram": {"enabled": False, "bot_token": "FILL_IN", "chat_id": "FILL_IN"},
        "discord": {"enabled": False, "webhook_url": "FILL_IN"},
    },
    "storage": {
        "sqlite_path": "data/alternate_model.db",
    },
    "http": {
        "timeout": 20,
        "delay_between_games": 0.4,  # be polite
    },
}

TZ = ZoneInfo(CONFIG["timezone"])


def _load_telegram_creds() -> None:
    """
    Load Telegram credentials from env vars (TG_BOT_TOKEN / TG_CHAT_ID) or a
    local telegram_creds.json, overriding the placeholders in CONFIG. Keeps the
    secret bot token out of the main script. Auto-enables telegram when both
    the token and chat id are present.
    """
    import os
    cfg = CONFIG["alerts"]["telegram"]
    tok = os.environ.get("TG_BOT_TOKEN")
    cid = os.environ.get("TG_CHAT_ID")
    for p in (Path("telegram_creds.json"),
              Path(__file__).resolve().with_name("telegram_creds.json")):
        if p.exists():
            try:
                d = json.loads(p.read_text())
                tok = tok or d.get("bot_token")
                cid = cid or d.get("chat_id")
            except Exception:
                pass
            break
    if tok:
        cfg["bot_token"] = tok
    if cid:
        cfg["chat_id"] = str(cid)
    if (cfg.get("bot_token") not in ("", "FILL_IN")
            and cfg.get("chat_id") not in ("", "FILL_IN")):
        cfg["enabled"] = True


_load_telegram_creds()


# =============================================================================
# ODDS MATH
# =============================================================================

def american_to_decimal(a: float) -> float:
    """American odds -> decimal odds."""
    a = float(a)
    if a >= 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)


def decimal_to_american(d: float) -> float:
    """Decimal odds -> American odds (rounded to nearest cent)."""
    d = float(d)
    if d >= 2.0:
        return round((d - 1.0) * 100.0)
    return round(-100.0 / (d - 1.0))


def fmt_american(a: float) -> str:
    a = int(round(a))
    return f"+{a}" if a >= 0 else f"{a}"


def margin_pct(side1_american: float, side2_american: float) -> float:
    """Book margin (vig) in percentage points for a two-sided market."""
    d1 = american_to_decimal(side1_american)
    d2 = american_to_decimal(side2_american)
    return (1.0 / d1 + 1.0 / d2 - 1.0) * 100.0


# =============================================================================
# DATABASE
# =============================================================================

def db_path() -> Path:
    p = Path(CONFIG["storage"]["sqlite_path"])
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league          TEXT NOT NULL,
    matchup_id      TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    start_utc       TEXT NOT NULL,
    start_local     TEXT NOT NULL,
    slate_date      TEXT NOT NULL,
    frozen          INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'open',  -- open | closed | graded | failed
    opened_at       TEXT,
    closed_at       TEXT,
    main_spread_line    REAL,
    main_total_line     REAL,
    close_main_spread_line REAL,
    close_main_total_line  REAL,
    final_home_score    INTEGER,
    final_away_score    INTEGER,
    UNIQUE(league, matchup_id)
);

CREATE TABLE IF NOT EXISTS lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    market_type     TEXT NOT NULL,        -- spread | total
    line_value      REAL NOT NULL,
    is_main         INTEGER NOT NULL DEFAULT 0,
    is_main_close   INTEGER NOT NULL DEFAULT 0,
    -- spread sides: home / away ; total sides: over / under
    side_a          TEXT NOT NULL,
    side_b          TEXT NOT NULL,
    open_a          REAL,
    open_b          REAL,
    close_a         REAL,
    close_b         REAL,
    margin_open     REAL,
    margin_close    REAL,
    UNIQUE(game_id, market_type, line_value)
);

CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    line_id         INTEGER NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    market_type     TEXT NOT NULL,
    line_value      REAL NOT NULL,
    is_main         INTEGER NOT NULL DEFAULT 0,
    signal_side     TEXT NOT NULL,         -- home|away|over|under
    signal_price_open  REAL,
    signal_price_close REAL,
    odds_move       REAL,
    margin_drop     REAL,
    promotion_bonus REAL,
    sharpness       REAL,
    rank_in_market  INTEGER,
    result          TEXT,                  -- WIN | LOSS | PUSH | NULL
    units           REAL NOT NULL DEFAULT 1.0,
    graded_at       TEXT,
    UNIQUE(line_id)
);

CREATE INDEX IF NOT EXISTS idx_games_slate ON games(slate_date, league);
CREATE INDEX IF NOT EXISTS idx_lines_game  ON lines(game_id, market_type);
CREATE INDEX IF NOT EXISTS idx_signals_game ON signals(game_id);
"""


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# =============================================================================
# PINNACLE CLIENT
# =============================================================================

class PinnacleClient:
    def __init__(self) -> None:
        cfg = CONFIG["pinnacle"]
        self.base = cfg["base"]
        self.version = cfg["version"]
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": cfg["api_key"],
            "Content-Language": "en-US",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.pinnacle.com/",
            "Origin": "https://www.pinnacle.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        })
        self.timeout = CONFIG["http"]["timeout"]

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base}/{self.version}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        return resp

    def get_matchups(self, league_id: int):
        """Fetch matchups for a league. NOTE: do NOT pass oddsFormat=decimal."""
        resp = self._get(f"/leagues/{league_id}/matchups")
        if resp.status_code == 204:
            return []
        resp.raise_for_status()
        return resp.json()

    def get_markets(self, matchup_id: str):
        """Fetch related straight markets for a matchup."""
        resp = self._get(f"/matchups/{matchup_id}/markets/related/straight")
        if resp.status_code == 204:
            return []
        resp.raise_for_status()
        return resp.json()


# =============================================================================
# MARKET PARSING
# =============================================================================

@dataclass
class ParsedLine:
    market_type: str          # spread | total
    line_value: float
    is_main: bool
    side_a: str               # home | over
    side_b: str               # away | under
    price_a: float
    price_b: float


def _parse_key(market: dict) -> tuple[str | None, float | None]:
    """
    Parse a market key like 's;0;s;-1.5' (spread) or 's;0;ou;8.5' (total) or 's;0;m' (moneyline).
    Returns (market_type, line_value).
    """
    key = market.get("key") or ""
    parts = key.split(";")
    mtype = None
    line = None
    if len(parts) >= 3:
        token = parts[2]
        if token == "s":
            mtype = "spread"
        elif token == "ou":
            mtype = "total"
        elif token == "m":
            mtype = "moneyline"
    # line value from key if present (not for moneyline)
    if len(parts) >= 4:
        try:
            line = float(parts[3])
        except (ValueError, TypeError):
            line = None
    return mtype, line


def parse_markets(markets: list[dict]) -> tuple[list[ParsedLine], dict]:
    """
    Parse the markets endpoint response into ParsedLine objects.
    Period 0 (full game) spread, total AND moneyline markets are kept.
    Also returns the detected main lines: {'spread': float, 'total': float, 'moneyline': 0.0}.
    Moneyline has line_value 0.0 (no handicap).
    """
    parsed: list[ParsedLine] = []
    main_lines: dict[str, float | None] = {"spread": None, "total": None, "moneyline": None}

    for m in markets:
        # period filter: full game only
        period = m.get("period", m.get("periodId"))
        try:
            period = int(period)
        except (ValueError, TypeError):
            period = 0
        if period != 0:
            continue

        mtype, line = _parse_key(m)
        if mtype is None:
            # fall back to explicit type field if present (exact matches only,
            # so 'team_total' / 'moneyline' are NOT misclassified)
            t = (m.get("type") or "").lower()
            if t in ("spread", "handicap"):
                mtype = "spread"
            elif t in ("total", "over_under", "overunder"):
                mtype = "total"
            elif t in ("moneyline", "money_line", "ml"):
                mtype = "moneyline"
        if mtype not in ("spread", "total", "moneyline"):
            continue

        # isAlternate can be True/False/None — None on moneylines = main
        is_alt_raw = m.get("isAlternate", False)
        if is_alt_raw is None:
            is_alt = False  # moneyline main
        else:
            is_alt = bool(is_alt_raw)

        # gather prices
        prices = m.get("prices") or []
        price_map: dict[str, float] = {}
        for p in prices:
            desig = (p.get("designation") or "").lower()
            pts = p.get("points")
            price = p.get("price")
            if price is None:
                continue
            try:
                price = float(price)
            except (ValueError, TypeError):
                continue
            if pts is not None and line is None:
                try:
                    line = float(pts)
                except (ValueError, TypeError):
                    pass
            # normalize designations
            if desig in ("home", "h", "team1", "participant1"):
                price_map["home"] = price
            elif desig in ("away", "a", "team2", "participant2"):
                price_map["away"] = price
            elif desig in ("over", "o"):
                price_map["over"] = price
            elif desig in ("under", "u"):
                price_map["under"] = price

        # moneyline has no line value — use 0.0
        if mtype == "moneyline":
            if line is None:
                line = 0.0
        if line is None:
            continue

        if mtype == "spread":
            if "home" not in price_map or "away" not in price_map:
                continue
            parsed.append(ParsedLine(
                market_type="spread",
                line_value=round(line, 3),
                is_main=not is_alt,
                side_a="home",
                side_b="away",
                price_a=price_map["home"],
                price_b=price_map["away"],
            ))
            if not is_alt:
                main_lines["spread"] = round(line, 3)
        elif mtype == "total":
            if "over" not in price_map or "under" not in price_map:
                continue
            parsed.append(ParsedLine(
                market_type="total",
                line_value=round(line, 3),
                is_main=not is_alt,
                side_a="over",
                side_b="under",
                price_a=price_map["over"],
                price_b=price_map["under"],
            ))
            if not is_alt:
                main_lines["total"] = round(line, 3)
        else:  # moneyline
            if "home" not in price_map or "away" not in price_map:
                continue
            parsed.append(ParsedLine(
                market_type="moneyline",
                line_value=0.0,
                is_main=not is_alt,
                side_a="home",
                side_b="away",
                price_a=price_map["home"],
                price_b=price_map["away"],
            ))
            if not is_alt:
                main_lines["moneyline"] = 0.0

    return parsed, main_lines


# =============================================================================
# MATCHUP PARSING
# =============================================================================

def parse_matchups(matchups: list[dict]) -> list[dict]:
    """
    Normalize matchup rows into:
      {matchup_id, home, away, start_utc (datetime)}
    """
    out = []
    for mu in matchups:
        # Only real head-to-head games. The feed also contains 'special' rows
        # (stand-alone totals like Over/Under, player props, exact-score, etc.)
        # which are NOT games and must be excluded.
        mtype = mu.get("type")
        if mtype is not None and mtype != "matchup":
            continue
        mid = mu.get("id") or mu.get("matchupId") or mu.get("externalId")
        if mid is None:
            continue
        start_raw = mu.get("startTime") or mu.get("startsAt") or mu.get("start")
        start_utc = _parse_utc(start_raw)
        if start_utc is None:
            continue

        # participants
        participants = mu.get("participants") or mu.get("teams") or []
        home = away = None
        for p in participants:
            name = (p.get("name") or p.get("teamName") or
                    (p.get("team") or {}).get("name") or "")
            align = (p.get("alignment") or p.get("side") or
                     p.get("homeAway") or "").lower()
            if align in ("home", "h", "team1"):
                home = name
            elif align in ("away", "a", "team2", "visitor"):
                away = name
        if home is None and len(participants) >= 2:
            # positional fallback: index 0 home, 1 away
            home = participants[0].get("name") or participants[0].get("teamName")
            away = participants[1].get("name") or participants[1].get("teamName")
        if not home or not away:
            continue

        out.append({
            "matchup_id": str(mid),
            "home": home,
            "away": away,
            "start_utc": start_utc,
        })
    return out


def _parse_utc(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        # epoch millis or seconds
        val = float(raw)
        if val > 1e12:
            val /= 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(raw, str):
        s = raw.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None


# =============================================================================
# COMMAND: open
# =============================================================================

def cmd_open(argv: list[str]) -> int:
    """
    Opening pull: capture every alternate spread & total for the slate.
    Usage: python alt_main.py open [YYYY-MM-DD]
    """
    init_db()
    target_date = argv[0] if argv else datetime.now(TZ).strftime("%Y-%m-%d")
    # validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: invalid date '{target_date}'. Use YYYY-MM-DD.")
        return 1

    client = PinnacleClient()
    conn = get_conn()
    total_games = 0

    print(f"\n📥 OPENING PULL — slate {target_date} ({CONFIG['timezone']})")
    print("=" * 60)

    for league in CONFIG["sports"]:
        league_id = CONFIG["league_ids"][league]
        try:
            raw = client.get_matchups(league_id)
        except requests.RequestException as e:
            print(f"  ⚠️  {league}: matchups fetch failed ({e})")
            continue

        matchups = parse_matchups(raw)
        league_count = 0
        for mu in matchups:
            start_utc = mu["start_utc"]
            start_local = start_utc.astimezone(TZ)
            if start_local.strftime("%Y-%m-%d") != target_date:
                continue

            # fetch markets
            try:
                markets = client.get_markets(mu["matchup_id"])
            except requests.RequestException as e:
                print(f"  ⚠️  {league} {mu['away']}@{mu['home']}: markets failed ({e})")
                time.sleep(CONFIG["http"]["delay_between_games"])
                continue

            parsed, main_lines = parse_markets(markets)
            # A real head-to-head game ALWAYS carries both a spread and a total
            # market. Rows missing either are league-wide specials that Pinnacle
            # lists as 'matchup' (e.g. 'Away Runs @ Home Runs') — skip them.
            has_spread = any(p.market_type == "spread" for p in parsed)
            has_total = any(p.market_type == "total" for p in parsed)
            if not (has_spread and has_total):
                time.sleep(CONFIG["http"]["delay_between_games"])
                continue

            now_iso = datetime.now(timezone.utc).isoformat()
            cur = conn.execute("""
                INSERT INTO games
                    (league, matchup_id, home_team, away_team, start_utc,
                     start_local, slate_date, frozen, status, opened_at,
                     main_spread_line, main_total_line)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'open', ?, ?, ?)
                ON CONFLICT(league, matchup_id) DO UPDATE SET
                    main_spread_line = excluded.main_spread_line,
                    main_total_line  = excluded.main_total_line
                RETURNING id;
            """, (
                league, mu["matchup_id"], mu["home"], mu["away"],
                start_utc.isoformat(), start_local.isoformat(), target_date,
                now_iso, main_lines.get("spread"), main_lines.get("total"),
            ))
            game_id = cur.fetchone()[0]

            # store every alternate line
            n_lines = 0
            for pl in parsed:
                conn.execute("""
                    INSERT INTO lines
                        (game_id, market_type, line_value, is_main, is_main_close,
                         side_a, side_b, open_a, open_b, margin_open)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(game_id, market_type, line_value) DO UPDATE SET
                        is_main     = excluded.is_main,
                        open_a      = excluded.open_a,
                        open_b      = excluded.open_b,
                        margin_open = excluded.margin_open;
                """, (
                    game_id, pl.market_type, pl.line_value,
                    1 if pl.is_main else 0, 1 if pl.is_main else 0,
                    pl.side_a, pl.side_b, pl.price_a, pl.price_b,
                    margin_pct(pl.price_a, pl.price_b),
                ))
                n_lines += 1

            conn.commit()
            league_count += 1
            total_games += 1
            spreads = sum(1 for p in parsed if p.market_type == "spread")
            totals = sum(1 for p in parsed if p.market_type == "total")
            ml = sum(1 for p in parsed if p.market_type == "moneyline")
            print(f"  ✅ {league.upper():4} {mu['away']} @ {mu['home']} "
                  f"[{start_local.strftime('%H:%M')}] — {ml} ML, {spreads} spreads, "
                  f"{totals} totals "
                  f"(main {main_lines.get('spread')} / {main_lines.get('total')} / ML {main_lines.get('moneyline') is not None})")

            time.sleep(CONFIG["http"]["delay_between_games"])

        if league_count == 0:
            print(f"  · {league.upper()}: no games on {target_date}")

    conn.close()
    print("=" * 60)
    print(f"🔒 SLATE FROZEN — {total_games} games captured for {target_date}.")
    print("   No late additions will be permitted (frozen_slate rule).")
    return 0


# =============================================================================
# COMMAND: close
# =============================================================================

def _games_in_t5_window(conn: sqlite3.Connection, target_game_id: int | None):
    """Return games that are within the T-5 closing window (or forced)."""
    now_utc = datetime.now(timezone.utc)
    rows = conn.execute("""
        SELECT * FROM games
        WHERE status = 'open'
        ORDER BY start_utc;
    """).fetchall()

    lo = CONFIG["capture"]["closing_window_min"]
    hi = CONFIG["capture"]["closing_window_max"]
    out = []
    for g in rows:
        start = datetime.fromisoformat(g["start_utc"])
        mins = (start - now_utc).total_seconds() / 60.0
        if target_game_id is not None:
            if g["id"] == target_game_id:
                out.append((g, mins))
        elif lo <= mins <= hi:
            out.append((g, mins))
    return out


def _close_one_game(client: "PinnacleClient", conn: sqlite3.Connection,
                    g: sqlite3.Row, mins: float, quiet: bool) -> bool:
    """Fetch the closing snapshot for one game, store it, alert passing picks.
    Returns True on success."""
    try:
        markets = client.get_markets(g["matchup_id"])
    except requests.RequestException as e:
        if not quiet:
            print(f"  ⚠️  #{g['id']} {g['away_team']}@{g['home_team']}: "
                  f"close fetch failed ({e})")
        return False

    parsed, main_lines = parse_markets(markets)
    now_iso = datetime.now(timezone.utc).isoformat()

    n_updated = 0
    for pl in parsed:
        # update existing line with closing prices
        cur = conn.execute("""
            UPDATE lines
            SET close_a = ?, close_b = ?, is_main_close = ?,
                margin_close = ?
            WHERE game_id = ? AND market_type = ? AND line_value = ?;
        """, (
            pl.price_a, pl.price_b, 1 if pl.is_main else 0,
            margin_pct(pl.price_a, pl.price_b),
            g["id"], pl.market_type, pl.line_value,
        ))
        if cur.rowcount == 0:
            # new alternate appeared at close — still record it (frozen-slate
            # rule applies to GAMES, not line additions; track every alternate)
            conn.execute("""
                INSERT INTO lines
                    (game_id, market_type, line_value, is_main, is_main_close,
                     side_a, side_b, open_a, open_b, close_a, close_b,
                     margin_open, margin_close)
                VALUES (?, ?, ?, 0, ?, ?, ?, NULL, NULL, ?, ?, NULL, ?)
                ON CONFLICT(game_id, market_type, line_value) DO UPDATE SET
                    close_a = excluded.close_a,
                    close_b = excluded.close_b,
                    is_main_close = excluded.is_main_close,
                    margin_close = excluded.margin_close;
            """, (
                g["id"], pl.market_type, pl.line_value,
                1 if pl.is_main else 0,
                pl.side_a, pl.side_b, pl.price_a, pl.price_b,
                margin_pct(pl.price_a, pl.price_b),
            ))
        n_updated += 1

    conn.execute("""
        UPDATE games
        SET status = 'closed', closed_at = ?,
            close_main_spread_line = ?, close_main_total_line = ?
        WHERE id = ?;
    """, (now_iso, main_lines.get("spread"), main_lines.get("total"), g["id"]))
    conn.commit()

    if quiet:
        print(f"[close] #{g['id']} {g['away_team']} @ {g['home_team']} "
              f"(T-{mins:.0f}m) — {n_updated} lines closed", flush=True)
    else:
        print(f"  ✅ #{g['id']} {g['away_team']} @ {g['home_team']} "
              f"(T-{mins:.0f}m) — {n_updated} lines closed")

    # analyze + ping any picks that pass (margin-drop rule survived)
    alert_game(conn, g)
    time.sleep(CONFIG["http"]["delay_between_games"])
    return True


def run_close_cycle(target_id: int | None = None, quiet: bool = False) -> int:
    """Run one closing-pull cycle and return the number of games closed.
    Safe to call repeatedly — only touches open games inside the T-5 window,
    so it is fully idempotent for the auto-runner."""
    init_db()
    client = PinnacleClient()
    conn = get_conn()
    window_games = _games_in_t5_window(conn, target_id)
    if window_games and not quiet:
        print("\n📤 CLOSING PULL (T-5 window)")
        print("=" * 60)
    closed = 0
    for g, mins in window_games:
        if _close_one_game(client, conn, g, mins, quiet):
            closed += 1
    conn.close()
    if window_games and not quiet:
        print("=" * 60)
    return closed


def cmd_close(argv: list[str]) -> int:
    """
    Closing pull: capture alternates for games 1-5 minutes from start.
    Usage: python alt_main.py close [game_id]
    """
    init_db()
    target_id = int(argv[0]) if argv else None
    conn = get_conn()
    window_games = _games_in_t5_window(conn, target_id)
    if not window_games:
        # also report upcoming games for operator awareness
        upcoming = conn.execute("""
            SELECT id, league, home_team, away_team, start_utc FROM games
            WHERE status = 'open' ORDER BY start_utc LIMIT 10;
        """).fetchall()
        print("⏳ No games in the T-5 closing window right now.")
        if upcoming:
            now_utc = datetime.now(timezone.utc)
            print("   Upcoming open games:")
            for g in upcoming:
                start = datetime.fromisoformat(g["start_utc"])
                mins = (start - now_utc).total_seconds() / 60.0
                print(f"     #{g['id']} {g['league'].upper()} "
                      f"{g['away_team']} @ {g['home_team']} — "
                      f"{mins:+.0f} min")
        conn.close()
        return 0
    conn.close()
    run_close_cycle(target_id, quiet=False)
    return 0



# =============================================================================
# ANALYSIS: movement, margin-drop, sharpness
# =============================================================================

@dataclass
class LineAnalysis:
    line_id: int
    market_type: str
    line_value: float
    is_main_open: bool
    is_main_close: bool
    side_a: str
    side_b: str
    open_a: float
    open_b: float
    close_a: float
    close_b: float
    margin_open: float
    margin_close: float
    margin_drop: float
    # signal side (the side that got bet / shortened)
    signal_side: str
    signal_price_open: float
    signal_price_close: float
    odds_move: float          # cents the signal side shortened
    promotion_bonus: float    # 0..1
    sharpness: float = 0.0
    rank: int = 0
    alive: bool = True        # survived margin-drop rule
    reason_dead: str = ""


def analyze_game(conn: sqlite3.Connection, game_id: int) -> dict:
    """
    Analyze all lines for a game. Returns dict with ranked spreads/totals/moneylines.
    Applies THE KEY RULE: margin must drop (by >= epsilon) or the line is killed.
    Whole market reading: ML + alt spreads + alt totals tell the story.
    """
    a_cfg = CONFIG["analysis"]
    r_cfg = CONFIG["ranking"]
    eps = a_cfg["margin_epsilon"]
    min_move = a_cfg["min_odds_move_cents"]

    rows = conn.execute("""
        SELECT * FROM lines WHERE game_id = ? ORDER BY market_type, line_value;
    """, (game_id,)).fetchall()

    # determine open/close main lines
    main_spread_open = main_spread_close = None
    main_total_open = main_total_close = None
    for r in rows:
        if r["is_main"] and r["market_type"] == "spread":
            main_spread_open = r["line_value"]
        if r["is_main_close"] and r["market_type"] == "spread":
            main_spread_close = r["line_value"]
        if r["is_main"] and r["market_type"] == "total":
            main_total_open = r["line_value"]
        if r["is_main_close"] and r["market_type"] == "total":
            main_total_close = r["line_value"]

    analyses: list[LineAnalysis] = []

    for r in rows:
        if r["open_a"] is None or r["close_a"] is None:
            continue  # incomplete data, skip

        open_a, open_b = r["open_a"], r["open_b"]
        close_a, close_b = r["close_a"], r["close_b"]
        m_open = r["margin_open"] if r["margin_open"] is not None else margin_pct(open_a, open_b)
        m_close = r["margin_close"] if r["margin_close"] is not None else margin_pct(close_a, close_b)
        margin_drop = m_open - m_close  # positive = margin compressed

        # --- THE KEY RULE: margin must drop ---
        alive = True
        reason = ""
        if a_cfg["margin_must_drop"]:
            if margin_drop < eps:
                alive = False
                if abs(margin_drop) < eps:
                    reason = "margin flat"
                else:
                    reason = "margin rose"

        # --- movement per side (shortened = bet) ---
        move_a = open_a - close_a   # >0 means side A price shortened (got bet)
        move_b = open_b - close_b

        # signal side = the side that shortened the most
        if move_a >= move_b:
            sig_side = r["side_a"]
            sig_move = move_a
            sig_open, sig_close = open_a, close_a
        else:
            sig_side = r["side_b"]
            sig_move = move_b
            sig_open, sig_close = open_b, close_b

        # qualifies on movement?
        if sig_move < min_move:
            if alive:
                alive = False
                reason = f"move {sig_move:.0f}¢ < {min_move}¢ min"

        # --- promotion bonus ---
        promo = _promotion_bonus(
            r["market_type"], r["line_value"],
            r["is_main"], r["is_main_close"],
            main_spread_open, main_spread_close,
            main_total_open, main_total_close,
        )

        analyses.append(LineAnalysis(
            line_id=r["id"],
            market_type=r["market_type"],
            line_value=r["line_value"],
            is_main_open=bool(r["is_main"]),
            is_main_close=bool(r["is_main_close"]),
            side_a=r["side_a"],
            side_b=r["side_b"],
            open_a=open_a, open_b=open_b,
            close_a=close_a, close_b=close_b,
            margin_open=m_open, margin_close=m_close,
            margin_drop=margin_drop,
            signal_side=sig_side,
            signal_price_open=sig_open,
            signal_price_close=sig_close,
            odds_move=sig_move,
            promotion_bonus=promo,
            alive=alive,
            reason_dead=reason,
        ))

    # --- normalize & score per market type ---
    result = {"spreads": [], "totals": [], "moneylines": [],
              "main_spread": main_spread_open, "main_total": main_total_open,
              "close_main_spread": main_spread_close, "close_main_total": main_total_close}

    for mtype, bucket in (("spread", "spreads"), ("total", "totals"), ("moneyline", "moneylines")):
        group = [a for a in analyses if a.market_type == mtype]
        alive_group = [a for a in group if a.alive]
        if alive_group:
            max_move = max(a.odds_move for a in alive_group) or 1.0
            max_drop = max(a.margin_drop for a in alive_group) or 1.0
            for a in alive_group:
                norm_move = a.odds_move / max_move if max_move else 0
                norm_drop = a.margin_drop / max_drop if max_drop else 0
                a.sharpness = (norm_move * r_cfg["odds_weight"] +
                               norm_drop * r_cfg["margin_weight"] +
                               a.promotion_bonus * r_cfg["promotion_weight"])
            alive_group.sort(key=lambda a: a.sharpness, reverse=True)
            for i, a in enumerate(alive_group, 1):
                a.rank = i

        # present alive first (ranked), then dead lines for transparency
        group.sort(key=lambda a: (not a.alive, -a.sharpness))
        result[bucket] = group

    return result


def _promotion_bonus(market_type: str, line_value: float,
                     is_main_open: bool, is_main_close: bool,
                     main_spread_open, main_spread_close,
                     main_total_open, main_total_close) -> float:
    """
    1.0 if this alternate was PROMOTED to main line at close.
    Partial credit (0..0.5) for moving closer to the main line.
    Moneyline has no promotion (only one line).
    """
    if market_type == "moneyline":
        return 0.0

    if not is_main_open and is_main_close:
        return 1.0  # alternate became the main line — very strong

    if market_type == "spread":
        main_open = main_spread_open
        main_close = main_spread_close
    else:
        main_open = main_total_open
        main_close = main_total_close

    if main_open is None or main_close is None:
        return 0.0
    if is_main_open:
        return 0.0  # already main, no promotion possible

    d_open = abs(line_value - main_open)
    d_close = abs(line_value - main_close)
    if d_close < d_open and d_open > 0:
        # moved closer to main line
        improvement = (d_open - d_close) / d_open
        return round(0.5 * improvement, 3)
    return 0.0


# =============================================================================
# COMMAND: rank
# =============================================================================

def _print_ranking(conn: sqlite3.Connection, game: sqlite3.Row, analysis: dict):
    league = game["league"].upper()
    print(f"\n🎯 SHARPEST ALTERNATE LINES — {league} · "
          f"{game['away_team']} v {game['home_team']}")
    print(f"   {datetime.fromisoformat(game['start_local']).strftime('%a %m/%d %H:%M')} "
          f"· game #{game['id']}")

    for label, bucket, main_key in (
        ("MONEYLINE", "moneylines", None),
        ("SPREADS", "spreads", "main_spread"),
        ("TOTALS", "totals", "main_total"),
    ):
        print(f"\n   {label} (ranked by sharpness):")
        group = analysis[bucket]
        if not group:
            print("      (no lines captured)")
            continue
        main_line = analysis.get(main_key) if main_key else None
        printed_alive = False
        for a in group:
            tag = ""
            if not a.alive:
                tag = f"  ☠ KILLED ({a.reason_dead})"
            else:
                printed_alive = True
                if a.rank == 1:
                    tag = "  ⭐ SHARPEST"
                elif a.is_main_open:
                    tag = "  [MAIN LINE]"

            move_txt = (f"{fmt_american(a.signal_price_open)} → "
                        f"{fmt_american(a.signal_price_close)} "
                        f"(↓{a.odds_move:.0f}¢)")
            margin_txt = (f"{a.margin_open:.1f}% → {a.margin_close:.1f}% "
                          f"(↓{a.margin_drop:.1f})")
            main_mark = " *" if a.is_main_open else ""
            print(f"      {a.rank if a.alive else '-':>2}. "
                  f"{a.signal_side.upper():5} {a.line_value:>6}{main_mark}   "
                  f"odds: {move_txt}   margin: {margin_txt}{tag}")
        if not printed_alive:
            print("      (no live alternates — all killed by margin rule)")


def cmd_rank(argv: list[str]) -> int:
    """
    Show ranked sharpest alternates for a game (or all closed games).
    Usage: python alt_main.py rank [game_id]
    """
    init_db()
    conn = get_conn()

    if argv:
        game_id = int(argv[0])
        game = conn.execute("SELECT * FROM games WHERE id = ?;", (game_id,)).fetchone()
        if not game:
            print(f"ERROR: no game #{game_id}")
            conn.close()
            return 1
        analysis = analyze_game(conn, game_id)
        _print_ranking(conn, game, analysis)
    else:
        games = conn.execute("""
            SELECT * FROM games WHERE status IN ('closed','graded')
            ORDER BY slate_date, start_local;
        """).fetchall()
        if not games:
            print("No closed games yet. Run `close` first.")
            conn.close()
            return 0
        for game in games:
            analysis = analyze_game(conn, game["id"])
            _print_ranking(conn, game, analysis)

    conn.close()
    return 0


# =============================================================================
# ESPN GRADING
# =============================================================================

def _normalize_name(name: str) -> set[str]:
    """Normalize a team name into a set of lowercase alnum tokens."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    # strip G1/G2 style markers
    tokens = []
    for tok in name.replace(".", " ").replace("-", " ").split():
        tok = tok.lower()
        tok = "".join(c for c in tok if c.isalnum())
        if tok and not tok.startswith("g") or (tok and tok not in ("g1", "g2")):
            tokens.append(tok)
    return set(t for t in tokens if t not in ("g1", "g2"))


def names_match(a: str, b: str) -> bool:
    """Token-subset match between two team names."""
    ta, tb = _normalize_name(a), _normalize_name(b)
    if not ta or not tb:
        return False
    # subset either direction, or strong overlap
    if ta <= tb or tb <= ta:
        return True
    inter = ta & tb
    return len(inter) >= max(1, min(len(ta), len(tb)) - 1)


def fetch_espn_scores(league: str, slate_date: str) -> list[dict]:
    """Fetch ESPN scoreboard for a league+date. Returns [{home,away,home_score,away_score}]."""
    url = CONFIG["espn"].get(league)
    if not url:
        return []
    params = {"dates": slate_date.replace("-", "")}
    try:
        resp = requests.get(url, params=params, timeout=CONFIG["http"]["timeout"],
                            headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  ⚠️  ESPN {league}: {e}")
        return []

    out = []
    for ev in data.get("events", []):
        for comp in ev.get("competitions", []):
            home = away = None
            hs = aw = None
            finished = False
            status = comp.get("status", {})
            stype = (status.get("type") or {})
            if stype.get("completed"):
                finished = True
            competitors = comp.get("competitors", [])
            for c in competitors:
                ha = (c.get("homeAway") or "").lower()
                team = (c.get("team") or {})
                name = (team.get("displayName") or team.get("name") or
                        team.get("shortDisplayName") or "")
                score = c.get("score")
                try:
                    score = int(score) if score not in (None, "") else None
                except (ValueError, TypeError):
                    score = None
                if ha == "home":
                    home, hs = name, score
                elif ha == "away":
                    away, aw = name, score
            if home and away and finished and hs is not None and aw is not None:
                out.append({"home": home, "away": away,
                            "home_score": hs, "away_score": aw})
    return out


def grade_game(conn: sqlite3.Connection, game: sqlite3.Row,
               home_score: int, away_score: int) -> None:
    """
    Grade all signals for a game against the actual result.
    Spread: favorite side covers if (fav_score - dog_score) > line magnitude.
    Total:  OVER wins if combined > line; UNDER wins if combined < line.
    """
    conn.execute("""
        UPDATE games SET status='graded', final_home_score=?, final_away_score=?
        WHERE id=?;
    """, (home_score, away_score, game["id"]))

    signals = conn.execute("""
        SELECT s.*, l.side_a, l.side_b
        FROM signals s JOIN lines l ON l.id = s.line_id
        WHERE s.game_id = ?;
    """, (game["id"],)).fetchall()

    home, away = game["home_team"], game["away_team"]
    for sig in signals:
        result = _grade_signal(sig, home, away, home_score, away_score)
        conn.execute("""
            UPDATE signals SET result=?, graded_at=? WHERE id=?;
        """, (result, datetime.now(timezone.utc).isoformat(), sig["id"]))
    conn.commit()


def _grade_signal(sig, home: str, away: str,
                  home_score: int, away_score: int) -> str:
    side = sig["signal_side"]
    line = sig["line_value"]
    mtype = sig["market_type"]

    if mtype == "total":
        combined = home_score + away_score
        if side == "over":
            if combined > line:
                return "WIN"
            if combined < line:
                return "LOSS"
            return "PUSH"
        else:  # under
            if combined < line:
                return "WIN"
            if combined > line:
                return "LOSS"
            return "PUSH"
    elif mtype == "moneyline":
        # ML: home wins if home_score > away_score
        if side == "home":
            if home_score > away_score:
                return "WIN"
            if home_score < away_score:
                return "LOSS"
            return "PUSH"
        else:  # away
            if away_score > home_score:
                return "WIN"
            if away_score < home_score:
                return "LOSS"
            return "PUSH"
    else:  # spread
        # the signal side is the side that got bet. The line_value is the
        # handicap applied to the HOME team (Pinnacle convention: negative =
        # home favored). Determine margin from that side's perspective.
        if side == "home":
            margin = home_score - away_score
        else:
            margin = away_score - home_score
        # For a spread, the bettor takes `side` at line_value (home handicap).
        # Away handicap = -line_value.
        if side == "home":
            adjusted = margin + line           # home + (its handicap)
        else:
            adjusted = margin - line           # away margin + away handicap (-line)
        if adjusted > 0:
            return "WIN"
        if adjusted < 0:
            return "LOSS"
        return "PUSH"


# =============================================================================
# SIGNAL PERSISTENCE
# =============================================================================

def build_and_store_signals(conn: sqlite3.Connection, game_id: int,
                            analysis: dict) -> None:
    """Store the ranked live signals for a game (replaces prior signals). Whole market: ML + spreads + totals."""
    conn.execute("DELETE FROM signals WHERE game_id = ?;", (game_id,))
    units = CONFIG["testing"]["flat_units"]
    for bucket in ("moneylines", "spreads", "totals"):
        for a in analysis[bucket]:
            if not a.alive:
                continue
            conn.execute("""
                INSERT INTO signals
                    (game_id, line_id, market_type, line_value, is_main,
                     signal_side, signal_price_open, signal_price_close,
                     odds_move, margin_drop, promotion_bonus, sharpness,
                     rank_in_market, units)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(line_id) DO UPDATE SET
                    sharpness = excluded.sharpness,
                    rank_in_market = excluded.rank_in_market;
            """, (
                game_id, a.line_id, a.market_type, a.line_value,
                1 if a.is_main_open else 0,
                a.signal_side, a.signal_price_open, a.signal_price_close,
                a.odds_move, a.margin_drop, a.promotion_bonus, a.sharpness,
                a.rank, units,
            ))
    conn.commit()


# =============================================================================
# TELEGRAM ALERTS
# =============================================================================

def send_telegram(text: str) -> bool:
    """Send a message via the Telegram Bot API. Returns True on success."""
    cfg = CONFIG["alerts"]["telegram"]
    if not cfg.get("enabled"):
        return False
    token = cfg.get("bot_token", "")
    chat_id = cfg.get("chat_id", "")
    if not token or token == "FILL_IN" or not chat_id or chat_id == "FILL_IN":
        print("  ⚠️  telegram enabled but bot_token / chat_id not configured")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        data = resp.json()
        if resp.ok and data.get("ok"):
            return True
        print(f"  ⚠️  telegram send failed: {data.get('description', resp.status_code)}")
        return False
    except requests.RequestException as e:
        print(f"  ⚠️  telegram send error: {e}")
        return False


def format_alt_alert(game: sqlite3.Row, analysis: dict) -> str | None:
    """
    Build the clean ALT Method alert (picks only): the sharpest live
    moneyline + alternate spread + total for a game. Whole market story.
    Returns None if no picks passed.
    """
    rows: list[str] = []
    found = False
    # Whole market: ML, SPREAD, TOTAL — read the market story
    for _label, bucket in (("ML", "moneylines"), ("SPREAD", "spreads"), ("TOTAL", "totals")):
        live = [a for a in analysis.get(bucket, []) if a.alive]
        if not live:
            continue
        a = live[0]  # rank 1 = sharpest
        found = True
        side = a.signal_side.upper()
        if a.market_type == "moneyline":
            # ML has no line value
            rows.append(f"<b>{_label} sharpest: {side} "
                        f"({fmt_american(a.signal_price_close)})</b>")
        else:
            rows.append(f"<b>{_label} sharpest: {side} {a.line_value} "
                        f"({fmt_american(a.signal_price_close)})</b>")
        rows.append(f"  moved {fmt_american(a.signal_price_open)} → "
                    f"{fmt_american(a.signal_price_close)} ({a.odds_move:.0f}¢ sharper)")
        rows.append(f"  margin {a.margin_open:.1f}% → {a.margin_close:.1f}% "
                    f"↓{a.margin_drop:.1f}")
        rows.append("")

    if not found:
        return None

    away = html.escape(game["away_team"])
    home = html.escape(game["home_team"])
    st = datetime.fromisoformat(game["start_local"]).strftime("%H:%M")
    header = [
        f"🎯 <b>ALT Method</b> · {game['league'].upper()}",
        f"<b>{away} v {home}</b>",
        f"⏱ closing snapshot · {st} CT",
        f"Whole market: ML + alts (Pinnacle sharp)",
        "",
    ]
    return "\n".join(header + rows).rstrip()


def alert_game(conn: sqlite3.Connection, game: sqlite3.Row) -> None:
    """Analyze a freshly-closed game, store signals, and ping passing picks."""
    analysis = analyze_game(conn, game["id"])
    build_and_store_signals(conn, game["id"], analysis)
    alert = format_alt_alert(game, analysis)
    if not alert:
        print(f"  ·  #{game['id']} — no picks passed (no margin-drop signals)")
        return
    sent = send_telegram(alert)
    if CONFIG["alerts"]["telegram"].get("enabled"):
        print(f"  {'📤 Telegram alert SENT' if sent else '⚠️  Telegram alert FAILED'} "
              f"· #{game['id']}")
    else:
        print(f"  ·  #{game['id']} — pick(s) passed but telegram disabled:")
        print("      " + alert.replace("\n", "\n      "))


def cmd_test_telegram(argv: list[str]) -> int:
    """Send a test ALT Method ping to verify the Telegram bot is connected."""
    cfg = CONFIG["alerts"]["telegram"]
    if not cfg.get("enabled") or cfg.get("bot_token") in ("", "FILL_IN") \
            or cfg.get("chat_id") in ("", "FILL_IN"):
        print("Telegram is not configured yet.")
        print("Set alerts.telegram.bot_token, chat_id, and enabled in CONFIG,")
        print("then re-run: python alt_main.py test-telegram")
        return 1
    msg = ("🎯 <b>ALT Method</b> · CONNECTION TEST\n"
           "Your bot is connected and picks will ping here at close (T-5).\n"
           "Label: <b>ALT Method</b>")
    ok = send_telegram(msg)
    print("✅ Test message sent — check Telegram." if ok
          else "❌ Test message failed — see error above.")
    return 0 if ok else 1


# =============================================================================
# COMMAND: report
# =============================================================================

def cmd_report(argv: list[str]) -> int:
    """
    Grade alternate-line signals vs actual results for a slate date.
    Usage: python alt_main.py report [YYYY-MM-DD]
    """
    init_db()
    conn = get_conn()
    target_date = argv[0] if argv else datetime.now(TZ).strftime("%Y-%m-%d")

    games = conn.execute("""
        SELECT * FROM games WHERE slate_date = ?
        ORDER BY league, start_local;
    """, (target_date,)).fetchall()
    if not games:
        print(f"No games on slate {target_date}.")
        conn.close()
        return 0

    # group games by league, fetch ESPN scores once per league
    scores_by_league: dict[str, list[dict]] = {}
    print(f"\n🎯 ALT-LINE DAILY — {target_date}")
    print("=" * 60)

    for g in games:
        league = g["league"]
        if league not in scores_by_league:
            scores_by_league[league] = fetch_espn_scores(league, target_date)

        scores = scores_by_league[league]
        match = next((s for s in scores
                      if names_match(s["home"], g["home_team"])
                      and names_match(s["away"], g["away_team"])), None)

        print(f"\n{league.upper()} · {g['away_team']} v {g['home_team']}")

        # build signals only if not already present (avoid wiping grades on re-run)
        existing = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE game_id = ?;", (g["id"],)
        ).fetchone()[0]
        if existing == 0:
            analysis = analyze_game(conn, g["id"])
            build_and_store_signals(conn, g["id"], analysis)

        if g["status"] != "graded":
            if not match:
                print("   ⏳ result not available yet (or team match failed)")
                continue
            grade_game(conn, g, match["home_score"], match["away_score"])
            print(f"   final: {match['away']} {match['away_score']} – "
                  f"{match['home']} {match['home_score']}")

        # print signal grades
        sigs = conn.execute("""
            SELECT * FROM signals WHERE game_id = ?
            ORDER BY market_type, rank_in_market;
        """, (g["id"],)).fetchall()
        if not sigs:
            print("   (no live signals)")
        for s in sigs:
            icon = {"WIN": "✅", "LOSS": "❌", "PUSH": "➖"}.get(s["result"], "⏳")
            star = "⭐" if s["rank_in_market"] == 1 else "  "
            print(f"   {icon} {star} {s['signal_side'].upper()} {s['line_value']} "
                  f"({fmt_american(s['signal_price_close'])}) · alt {s['market_type']} "
                  f"· sharper by {s['odds_move']:.0f}¢ · margin ↓{s['margin_drop']:.1f} "
                  f"→ {s['result'] or 'PENDING'}")

    # summary
    _print_alt_summary(conn, target_date)
    conn.close()
    return 0


def _print_alt_summary(conn: sqlite3.Connection, target_date: str) -> None:
    rows = conn.execute("""
        SELECT s.result, s.rank_in_market, s.market_type
        FROM signals s JOIN games g ON g.id = s.game_id
        WHERE g.slate_date = ?;
    """, (target_date,)).fetchall()

    def tally(pred):
        w = sum(1 for r in rows if pred(r) and r["result"] == "WIN")
        l = sum(1 for r in rows if pred(r) and r["result"] == "LOSS")
        p = sum(1 for r in rows if pred(r) and r["result"] == "PUSH")
        return w, l, p

    print("\n" + "-" * 60)
    # sharpest (rank 1) per market
    sw, sl, sp = tally(lambda r: r["rank_in_market"] == 1)
    aw, al, ap = tally(lambda r: True)
    print(f"Sharpest-number record: {sw}-{sl}"
          + (f" ({sp} push)" if sp else ""))
    print(f"All live alternates:    {aw}-{al}"
          + (f" ({ap} push)" if ap else ""))
    print(f"Testing size: {CONFIG['testing']['flat_units']}u flat per play")


# =============================================================================
# COMMAND: compare
# =============================================================================

def cmd_compare(argv: list[str]) -> int:
    """
    Compare alt-line performance vs main-line performance for a slate.
    Usage: python alt_main.py compare [YYYY-MM-DD]
    """
    init_db()
    conn = get_conn()
    target_date = argv[0] if argv else datetime.now(TZ).strftime("%Y-%m-%d")

    games = conn.execute("""
        SELECT * FROM games WHERE slate_date = ? AND status = 'graded'
        ORDER BY league, start_local;
    """, (target_date,)).fetchall()
    if not games:
        print(f"No graded games on {target_date}. Run `report` first.")
        conn.close()
        return 0

    print(f"\n🎯 ALT-LINE vs MAIN-LINE — {target_date}")
    print("=" * 60)

    # --- ALT: sharpest alternate per market (rank 1, non-main OR any rank1) ---
    alt_rows = conn.execute("""
        SELECT s.*, g.home_team, g.away_team, g.league
        FROM signals s JOIN games g ON g.id = s.game_id
        WHERE g.slate_date = ? AND s.rank_in_market = 1;
    """, (target_date,)).fetchall()

    # --- MAIN: the main line signal per market (is_main = 1) ---
    main_rows = conn.execute("""
        SELECT s.*, g.home_team, g.away_team, g.league
        FROM signals s JOIN games g ON g.id = s.game_id
        WHERE g.slate_date = ? AND s.is_main = 1;
    """, (target_date,)).fetchall()

    def record(rows):
        w = sum(1 for r in rows if r["result"] == "WIN")
        l = sum(1 for r in rows if r["result"] == "LOSS")
        p = sum(1 for r in rows if r["result"] == "PUSH")
        return w, l, p

    # print per-game comparison
    seen = set()
    for g in games:
        key = g["id"]
        if key in seen:
            continue
        seen.add(key)
        print(f"\n{g['league'].upper()} · {g['away_team']} v {g['home_team']} "
              f"({g['final_away_score']}–{g['final_home_score']})")
        for r in alt_rows:
            if r["game_id"] == g["id"]:
                icon = {"WIN": "✅", "LOSS": "❌", "PUSH": "➖"}.get(r["result"], "⏳")
                print(f"   ALT  {icon} {r['signal_side'].upper()} {r['line_value']} "
                      f"({fmt_american(r['signal_price_close'])}) "
                      f"sharper {r['odds_move']:.0f}¢ → {r['result'] or 'PENDING'}")
        for r in main_rows:
            if r["game_id"] == g["id"]:
                icon = {"WIN": "✅", "LOSS": "❌", "PUSH": "➖"}.get(r["result"], "⏳")
                print(f"   MAIN {icon} {r['signal_side'].upper()} {r['line_value']} "
                      f"({fmt_american(r['signal_price_close'])}) "
                      f"sharper {r['odds_move']:.0f}¢ → {r['result'] or 'PENDING'}")

    aw, al, ap = record(alt_rows)
    mw, ml, mp = record(main_rows)
    print("\n" + "-" * 60)
    print(f"Alt-line (sharpest #) record:  {aw}-{al}"
          + (f" ({ap} push)" if ap else ""))
    print(f"Main-line record:              {mw}-{ml}"
          + (f" ({mp} push)" if mp else ""))
    diff = (aw - al) - (mw - ml)
    if diff > 0:
        print(f"Alt-edge: +{diff} pick(s) — alternates outperforming.")
    elif diff < 0:
        print(f"Alt-edge: {diff} pick(s) — main line outperforming.")
    else:
        print("Alt-edge: even — no edge yet.")

    # cumulative testing stats
    total_graded = conn.execute("""
        SELECT COUNT(*) FROM signals s JOIN games g ON g.id=s.game_id
        WHERE s.result IN ('WIN','LOSS','PUSH');
    """).fetchone()[0]
    threshold = CONFIG["testing"]["variable_sizing_after"]
    print(f"\nGraded alternates to date: {total_graded} / {threshold} "
          f"before variable sizing.")
    conn.close()
    return 0


# =============================================================================
# COMMAND: status / config
# =============================================================================

def cmd_status(argv: list[str]) -> int:
    init_db()
    conn = get_conn()
    rows = conn.execute("""
        SELECT slate_date, league, status, COUNT(*) c
        FROM games GROUP BY slate_date, league, status
        ORDER BY slate_date DESC, league;
    """).fetchall()
    if not rows:
        print("No games captured yet. Run `python alt_main.py open YYYY-MM-DD`.")
        conn.close()
        return 0
    print("\n📊 SLATE STATUS")
    print("=" * 60)
    cur_date = None
    for r in rows:
        if r["slate_date"] != cur_date:
            cur_date = r["slate_date"]
            print(f"\n  {cur_date}")
        print(f"     {r['league'].upper():5} {r['status']:8} {r['c']} game(s)")
    conn.close()
    return 0


def cmd_config(argv: list[str]) -> int:
    # redact alert secrets
    safe = json.loads(json.dumps(CONFIG))
    for key in ("telegram", "discord"):
        if key in safe["alerts"]:
            for field in ("bot_token", "chat_id", "webhook_url"):
                if field in safe["alerts"][key]:
                    safe["alerts"][key][field] = "***"
    print(json.dumps(safe, indent=2))
    return 0


# =============================================================================
# CLI DISPATCH
# =============================================================================

COMMANDS = {
    "open": cmd_open,
    "close": cmd_close,
    "rank": cmd_rank,
    "report": cmd_report,
    "compare": cmd_compare,
    "status": cmd_status,
    "config": cmd_config,
    "test-telegram": cmd_test_telegram,
}

USAGE = """Alternate-Line CLV Method

Usage:
  python alt_main.py open [YYYY-MM-DD]     capture all alternates for a slate
  python alt_main.py close [game_id]       T-5 closing pull (games 1-5 min out)
  python alt_main.py rank [game_id]        ranked sharpest alternates
  python alt_main.py report [YYYY-MM-DD]   grade alt signals vs results
  python alt_main.py compare [YYYY-MM-DD]  alt-line vs main-line performance
  python alt_main.py status                slate overview
  python alt_main.py config                print configuration
  python alt_main.py test-telegram         send a test ALT Method ping
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd = argv[0].lower()
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}\n")
        print(USAGE)
        return 1
    return COMMANDS[cmd](argv[1:])


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
