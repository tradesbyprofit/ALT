"""Live end-to-end test: force Rockies into the T-5 window, run the runner's
close path (real Pinnacle fetch + real Telegram ping), then fully restore the
game to 'open' so tonight's actual T-5 capture is unaffected."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone, timedelta
import alt_main as am

GID = 15  # Colorado Rockies @ Milwaukee Brewers
conn = am.get_conn()
orig = conn.execute("SELECT start_utc FROM games WHERE id=?", (GID,)).fetchone()["start_utc"]
print(f"original start_utc: {orig}")

try:
    # shift start to now + 3 min (inside the [1,5] window)
    fake_start = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
    conn.execute("UPDATE games SET start_utc=? WHERE id=?", (fake_start, GID))
    conn.commit()
    print(f"shifted start_utc:  {fake_start}  (window test)")
    print("\n--- running runner close cycle (quiet) ---")
    closed = am.run_close_cycle(quiet=True)
    print(f"\nclosed this cycle: {closed}")

    g = conn.execute("SELECT status, closed_at FROM games WHERE id=?", (GID,)).fetchone()
    nlines = conn.execute("SELECT COUNT(*) FROM lines WHERE game_id=? AND close_a IS NOT NULL", (GID,)).fetchone()[0]
    nsig = conn.execute("SELECT COUNT(*) FROM signals WHERE game_id=?", (GID,)).fetchone()[0]
    print(f"game status={g['status']}  lines_with_close={nlines}  signals_built={nsig}")
    assert g["status"] == "closed", "game should be closed"
    assert nlines > 0, "close prices should be stored"
    print("\n✅ END-TO-END OK — check Telegram for the ALT Method Rockies ping.")
finally:
    # ---- full restore so tonight's T-5 capture is clean ----
    conn.execute("UPDATE games SET start_utc=?, status='open', closed_at=NULL, "
                 "close_main_spread_line=NULL, close_main_total_line=NULL WHERE id=?",
                 (orig, GID))
    conn.execute("UPDATE lines SET close_a=NULL, close_b=NULL, margin_close=NULL, "
                 "is_main_close=is_main WHERE game_id=?", (GID,))
    conn.execute("DELETE FROM signals WHERE game_id=?", (GID,))
    conn.commit()
    g = conn.execute("SELECT status, closed_at FROM games WHERE id=?", (GID,)).fetchone()
    nopen_lines = conn.execute("SELECT COUNT(*) FROM lines WHERE game_id=? AND close_a IS NULL", (GID,)).fetchone()[0]
    nsig = conn.execute("SELECT COUNT(*) FROM signals WHERE game_id=?", (GID,)).fetchone()[0]
    rst = conn.execute("SELECT start_utc FROM games WHERE id=?", (GID,)).fetchone()["start_utc"]
    print(f"\n[restore] status={g['status']}  start_utc={rst}  "
          f"open_lines={nopen_lines}  signals={nsig}")
    assert g["status"] == "open" and rst == orig and nsig == 0
    print("[restore] ✔ game reset to open with original start time")
conn.close()
