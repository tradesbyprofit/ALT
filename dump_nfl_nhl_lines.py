#!/usr/bin/env python3
"""
One-off diagnostic: pull EVERY alternate spread/total/moneyline line for
NFL and NHL for a given slate date directly from Pinnacle and print a
markdown log of the opening lines (same format as mlb_frozen_lines_*.md).

Usage: python dump_nfl_nhl_lines.py [YYYY-MM-DD]
"""
import sys
from datetime import datetime

import alt_main as am

TARGET_DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.now(am.TZ).strftime("%Y-%m-%d")
LEAGUES = ["nfl", "nhl"]


def render_game_md(league, mu, parsed, main_lines, idx):
    start_local = mu["start_utc"].astimezone(am.TZ)
    lines_out = []
    lines_out.append(
        f"## [{league.upper()}] {mu['away']} @ {mu['home']}  ·  "
        f"{start_local.strftime('%H:%M')}  ·  #{idx}\n"
    )
    lines_out.append(
        f"Main: spread {main_lines.get('spread')} · total {main_lines.get('total')}\n"
    )

    spreads = sorted([p for p in parsed if p.market_type == "spread"], key=lambda p: p.line_value)
    totals = sorted([p for p in parsed if p.market_type == "total"], key=lambda p: p.line_value)
    mls = [p for p in parsed if p.market_type == "moneyline"]

    if mls:
        lines_out.append("**Moneyline**\n")
        lines_out.append("| home | away | max limit |")
        lines_out.append("|---:|---:|---:|")
        for p in mls:
            lim = f"${p.max_limit:,.0f}" if p.max_limit is not None else "—"
            lines_out.append(f"| {p.price_a:+.0f} | {p.price_b:+.0f} | {lim} |")
        lines_out.append("")

    if spreads:
        lines_out.append("**Spreads** (line = home handicap)\n")
        lines_out.append("| line | home | away | margin | max limit | |")
        lines_out.append("|---:|---:|---:|---:|---:|:--:|")
        for p in spreads:
            star = "★" if p.is_main else ""
            margin = am.margin_pct(p.price_a, p.price_b)
            lim = f"${p.max_limit:,.0f}" if p.max_limit is not None else "—"
            lines_out.append(
                f"| {p.line_value:+g} | {p.price_a:+.0f} | {p.price_b:+.0f} | {margin:.2f}% | {lim} | {star} |"
            )
        lines_out.append("")

    if totals:
        lines_out.append("**Totals**\n")
        lines_out.append("| line | over | under | margin | max limit | |")
        lines_out.append("|---:|---:|---:|---:|---:|:--:|")
        for p in totals:
            star = "★" if p.is_main else ""
            margin = am.margin_pct(p.price_a, p.price_b)
            lim = f"${p.max_limit:,.0f}" if p.max_limit is not None else "—"
            lines_out.append(
                f"| {p.line_value:g} | {p.price_a:+.0f} | {p.price_b:+.0f} | {margin:.2f}% | {lim} | {star} |"
            )
        lines_out.append("")

    return "\n".join(lines_out)



def main():
    client = am.PinnacleClient()
    out_md = [f"# NFL & NHL Opening Alternate Lines — Slate {TARGET_DATE} ({am.CONFIG['timezone']})\n"]
    out_md.append("> Main line marked with ★. Odds are American, pulled at opening/diagnostic time.\n")

    total_games = 0
    for league in LEAGUES:
        league_id = am.CONFIG["league_ids"][league]
        print(f"\n=== {league.upper()} (league_id={league_id}) ===", flush=True)
        try:
            raw = client.get_matchups(league_id)
        except Exception as e:
            print(f"  ⚠️  {league}: league-level matchups fetch FAILED: {e}", flush=True)
            sport_id = am.CONFIG["sport_ids"][league]
            try:
                print(f"  ...trying sport-level fallback /sports/{sport_id}/matchups", flush=True)
                resp = client.session.get(
                    f"{client.base}/{client.version}/sports/{sport_id}/matchups",
                    timeout=client.timeout,
                )
                print(f"  sport-level status: {resp.status_code}", flush=True)
                if resp.status_code == 200:
                    raw_all = resp.json()
                    # sport-level feed includes every league in that sport (e.g.
                    # NCAAF + NFL under american football) - filter to our league_id
                    raw = [
                        m for m in raw_all
                        if (m.get("league") or {}).get("id") == league_id
                    ]
                    print(
                        f"  ✅ sport-level fallback worked, {len(raw_all)} total matchups "
                        f"in sport, {len(raw)} match league_id={league_id}",
                        flush=True,
                    )
                else:
                    print(f"  body: {resp.text[:300]}", flush=True)
                    continue
            except Exception as e2:
                print(f"  sport-level fallback also FAILED: {e2}", flush=True)
                continue

        matchups = am.parse_matchups(raw)
        print(f"  total matchups returned by Pinnacle: {len(matchups)}", flush=True)
        league_count = 0
        for mu in matchups:
            start_local = mu["start_utc"].astimezone(am.TZ)
            if start_local.strftime("%Y-%m-%d") != TARGET_DATE:
                continue
            try:
                markets = client.get_markets(mu["matchup_id"])
            except Exception as e:
                print(f"  ⚠️  {mu['away']}@{mu['home']}: markets FAILED: {e}", flush=True)
                continue

            parsed, main_lines = am.parse_markets(markets)
            has_spread = any(p.market_type == "spread" for p in parsed)
            has_total = any(p.market_type == "total" for p in parsed)
            print(
                f"  ✅ {mu['away']} @ {mu['home']} [{start_local.strftime('%H:%M')}] "
                f"— {len(parsed)} total line rows (spread={has_spread}, total={has_total})",
                flush=True,
            )
            league_count += 1
            total_games += 1
            out_md.append(render_game_md(league, mu, parsed, main_lines, total_games))

        if league_count == 0:
            print(f"  · {league.upper()}: no games found on {TARGET_DATE}", flush=True)

    print(f"\n=== TOTAL GAMES CAPTURED: {total_games} ===", flush=True)

    print("\n----BEGIN-MARKDOWN----", flush=True)
    print("\n".join(out_md), flush=True)
    print("----END-MARKDOWN----", flush=True)


if __name__ == "__main__":
    main()
