#!/usr/bin/env python3
"""Diagnostic: discover correct Pinnacle league IDs for NFL / NHL this season
by listing every league under the parent sport and matching by name, since
real games exist tonight (10/9/2026) but the hardcoded league_ids (NFL=676,
NHL=579) are returning 0 matchups."""
import alt_main as am

for label, sport_id in [("American Football (NFL lives here)", 6), ("Ice Hockey (NHL lives here)", 5)]:
    print(f"\n=== sport_id={sport_id} — {label} ===", flush=True)
    try:
        resp = am.PinnacleClient().session.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/sports/{sport_id}/matchups",
            timeout=20,
        )
        print(f"status: {resp.status_code}", flush=True)
        if resp.status_code != 200:
            print(f"body: {resp.text[:500]}", flush=True)
            continue
        data = resp.json()
        print(f"total matchups in sport: {len(data)}", flush=True)
        leagues_seen = {}
        for m in data:
            lg = m.get("league") or {}
            key = (lg.get("id"), lg.get("name"))
            leagues_seen[key] = leagues_seen.get(key, 0) + 1
        for (lid, lname), count in sorted(leagues_seen.items(), key=lambda x: -x[1]):
            print(f"  league_id={lid}  name={lname!r}  matchups={count}", flush=True)
    except Exception as e:
        print(f"FAILED: {e}", flush=True)

# also try the well-known Pinnacle sports listing endpoint for cross-check
print("\n=== /0.1/sports (full list) ===", flush=True)
try:
    resp = am.PinnacleClient().session.get(
        "https://guest.api.arcadia.pinnacle.com/0.1/sports", timeout=20
    )
    print(f"status: {resp.status_code}", flush=True)
    if resp.status_code == 200:
        for s in resp.json():
            if s.get("matchupCount", 0) > 0:
                print(f"  id={s.get('id')} name={s.get('name')!r} matchupCount={s.get('matchupCount')}", flush=True)
except Exception as e:
    print(f"FAILED: {e}", flush=True)
