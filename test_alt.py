"""Synthetic test for alt_main.py analysis engine (no live API)."""
import os, sqlite3
from datetime import datetime, timezone, timedelta

# use a throwaway db
os.environ.setdefault("X", "1")
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alt_main as am
am.CONFIG["storage"]["sqlite_path"] = "data/test_alt.db"
if os.path.exists("data/test_alt.db"):
    os.remove("data/test_alt.db")
am.init_db()

# ---- odds math sanity ----
assert abs(am.american_to_decimal(-110) - 1.909090) < 1e-4
assert abs(am.american_to_decimal(+150) - 2.5) < 1e-9
assert am.decimal_to_american(2.5) == 150
assert am.decimal_to_american(1.9090909) == -110
m = am.margin_pct(-110, -110)
assert abs(m - 4.7619) < 0.01, m
print(f"[odds] american<->decimal + margin OK  (juice -110/-110 = {m:.2f}%)")

# ---- build a synthetic game: Red Sox @ Yankees ----
conn = am.get_conn()
now = datetime.now(timezone.utc)
start = (now + timedelta(minutes=3)).isoformat()
cur = conn.execute("""
    INSERT INTO games (league, matchup_id, home_team, away_team, start_utc,
        start_local, slate_date, frozen, status, opened_at,
        main_spread_line, main_total_line, close_main_spread_line, close_main_total_line)
    VALUES ('mlb','TEST1','Yankees','Red Sox',?,?,'2026-07-24',1,'closed',?, -1.5, 8.5, -1.5, 8.5)
    RETURNING id;
""", (start, start, now.isoformat()))
gid = cur.fetchone()[0]

# spreads: (line, is_main, open_home, open_away, close_home, close_away)
# Numbers chosen so the margin math is internally consistent (margin truly
# drops for the sharp lines, rises for the killed line).
spreads = [
    (-1.0, 0, 135, -162, 108, -118),   # SHARPEST: home +135->+108 (27c), margin 4.2%->2.1%
    (-1.5, 1, 147, -170, 133, -148),   # main line: home +147->+133 (14c), margin 3.45->2.60
    (-2.0, 0, 247, -320, 230, -290),   # home +247->+230 (17c), margin 5.01->4.66
    (-2.5, 0, 330, -450, 315, -430),   # home +330->+315 (15c) but margin 5.07->5.23 ROSE -> killed
]
for line, ismain, oa, ob, ca, cb in spreads:
    conn.execute("""
        INSERT INTO lines (game_id, market_type, line_value, is_main, is_main_close,
            side_a, side_b, open_a, open_b, close_a, close_b, margin_open, margin_close)
        VALUES (?, 'spread', ?, ?, ?, 'home','away', ?,?,?,?, ?, ?);
    """, (gid, line, ismain, ismain, oa, ob, ca, cb,
          am.margin_pct(oa, ob), am.margin_pct(ca, cb)))

# totals: (line, is_main, open_over, open_under, close_over, close_under)
totals = [
    (8.0, 0, 108, -124, 102, -116),    # SHARPEST: over +108->+102 (6c), margin 3.43->3.21
    (8.5, 1, -105, -110, -112, -103),  # main line: over -105->-112 (7c), margin 3.60->3.57
    (9.0, 0, -140, 118, -138, 116),    # over -140->-138 (2c <5) AND margin 4.21->4.28 ROSE -> killed
]
for line, ismain, oa, ob, ca, cb in totals:
    conn.execute("""
        INSERT INTO lines (game_id, market_type, line_value, is_main, is_main_close,
            side_a, side_b, open_a, open_b, close_a, close_b, margin_open, margin_close)
        VALUES (?, 'total', ?, ?, ?, 'over','under', ?,?,?,?, ?, ?);
    """, (gid, line, ismain, ismain, oa, ob, ca, cb,
          am.margin_pct(oa, ob), am.margin_pct(ca, cb)))
conn.commit()

# ---- run analysis ----
analysis = am.analyze_game(conn, gid)
print("\n--- SPREADS ---")
for a in analysis["spreads"]:
    print(f"  line {a.line_value:>5} alive={a.alive:<5} rank={a.rank} "
          f"sig={a.signal_side} move={a.odds_move:.0f}c "
          f"mdrop={a.margin_drop:.2f} sharp={a.sharpness:.3f} {a.reason_dead}")
print("--- TOTALS ---")
for a in analysis["totals"]:
    print(f"  line {a.line_value:>5} alive={a.alive:<5} rank={a.rank} "
          f"sig={a.signal_side} move={a.odds_move:.0f}c "
          f"mdrop={a.margin_drop:.2f} sharp={a.sharpness:.3f} {a.reason_dead}")

alive_spreads = [a for a in analysis["spreads"] if a.alive]
alive_totals = [a for a in analysis["totals"] if a.alive]
assert alive_spreads[0].line_value == -1.0, "expected -1.0 sharpest spread"
assert alive_totals[0].line_value == 8.0, "expected 8.0 sharpest total"
# -2.5 spread should be killed (margin rose)
killed = [a for a in analysis["spreads"] if not a.alive]
assert any(a.line_value == -2.5 for a in killed), "-2.5 should be killed (margin rose)"
print("\n[rank] -1.0 is sharpest spread, 8.0 sharpest total, -2.5 killed ✔")

# ---- store signals + grade ----
am.build_and_store_signals(conn, gid, analysis)
sigs = conn.execute("SELECT * FROM signals").fetchall()
print(f"\n[signals] stored {len(sigs)} live signals")
# 3 surviving spreads (one killed) + 2 surviving totals (one killed) = 5
assert len(sigs) == 5, len(sigs)

# grade: Yankees 5, Red Sox 3 -> combined 8
am.grade_game(conn, conn.execute("SELECT * FROM games WHERE id=?",(gid,)).fetchone(), 5, 3)
for s in conn.execute("SELECT * FROM signals").fetchall():
    print(f"  {s['market_type']:6} {s['signal_side']:5} {s['line_value']:>5} "
          f"-> {s['result']}")

# verify spread -1.0 home (Yankees): margin = 5-3 = 2, adjusted = 2 + (-1.0) = 1 > 0 WIN
r = conn.execute("SELECT result FROM signals WHERE market_type='spread' AND line_value=-1.0").fetchone()
assert r["result"] == "WIN", r["result"]
# total 8.0 over: combined 8 == line 8 -> PUSH
r = conn.execute("SELECT result FROM signals WHERE market_type='total' AND line_value=8.0").fetchone()
assert r["result"] == "PUSH", r["result"]
print("\n[grade] spread -1.0 home WIN, total 8.0 over PUSH ✔")

# ---- name matching ----
assert am.names_match("New York Yankees", "Yankees")
assert am.names_match("Boston Red Sox", "red sox")
assert not am.names_match("Yankees", "Red Sox")
print("[names] token-subset matching ✔")
conn.close()
print("\nALL TESTS PASSED ✔")
