"""Drive the CLI display commands against the synthetic test DB."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alt_main as am
am.CONFIG["storage"]["sqlite_path"] = "data/test_alt.db"

print("############ RANK ############")
am.cmd_rank(["1"])
print("\n############ REPORT ############")
am.cmd_report(["2026-07-24"])
print("\n############ COMPARE ############")
am.cmd_compare(["2026-07-24"])
print("\n############ STATUS ############")
am.cmd_status([])
