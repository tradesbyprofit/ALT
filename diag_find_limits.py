#!/usr/bin/env python3
"""Diagnostic: inspect raw Pinnacle markets JSON for one live matchup to find
where bet limits (max stake) live in the payload, since alt_main.py's parser
currently only extracts price/points and drops everything else."""
import json
import sys

import alt_main as am


def find_limit_keys(obj, path="", seen=None):
    """Recursively search for any key containing 'limit' (case-insensitive)."""
    if seen is None:
        seen = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if "limit" in k.lower():
                seen.append((p, v))
            find_limit_keys(v, p, seen)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):  # sample first few list items only
            find_limit_keys(v, f"{path}[{i}]", seen)
    return seen


def main():
    client = am.PinnacleClient()
    league_id = am.CONFIG["league_ids"]["nhl"]
    raw = client.get_matchups(league_id)
    matchups = am.parse_matchups(raw)
    if not matchups:
        print("No NHL matchups found right now.")
        return

    mu = matchups[0]
    print(f"Inspecting: {mu['away']} @ {mu['home']} (matchup_id={mu['matchup_id']})", flush=True)
    markets = client.get_markets(mu["matchup_id"])
    print(f"\n--- total market rows: {len(markets)} ---", flush=True)

    # print the raw JSON of the FIRST market row in full, so we can see every field
    if markets:
        print("\n--- FULL RAW JSON of first market row ---", flush=True)
        print(json.dumps(markets[0], indent=2, default=str), flush=True)

    # search all rows for anything limit-related
    print("\n--- keys containing 'limit' across all market rows (first 5 hits) ---", flush=True)
    hits = find_limit_keys(markets)
    for p, v in hits[:20]:
        print(f"  {p} = {v}", flush=True)
    if not hits:
        print("  (none found at market level)", flush=True)

    # also check the matchup-level raw object and the straight matchup detail endpoint
    print("\n--- raw matchup object keys (top-level) ---", flush=True)
    raw_mu = next((m for m in raw if (m.get("id") or m.get("matchupId")) == mu["matchup_id"]), None)
    if raw_mu:
        print(json.dumps(list(raw_mu.keys())), flush=True)
        hits2 = find_limit_keys(raw_mu)
        for p, v in hits2[:20]:
            print(f"  matchup.{p} = {v}", flush=True)

    # try the special-markets / matchup detail endpoint too, in case limits live there
    try:
        resp = client.session.get(
            f"{client.base}/{client.version}/matchups/{mu['matchup_id']}/related",
            timeout=client.timeout,
        )
        print(f"\n--- /matchups/{{id}}/related status: {resp.status_code} ---", flush=True)
        if resp.status_code == 200:
            data = resp.json()
            print(json.dumps(data, indent=2, default=str)[:3000], flush=True)
    except Exception as e:
        print(f"related endpoint failed: {e}", flush=True)


if __name__ == "__main__":
    main()
