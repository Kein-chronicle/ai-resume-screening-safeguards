#!/usr/bin/env python3
"""Deterministic career arithmetic. The model only EXTRACTS date strings (with a verified quote); code computes.
Union of overlapping positions, gaps >= GAP_MONTHS (shown as questions, NEVER as a penalty), unknown dates excluded and reported.
usage: career_facts.py positions.json [--as-of YYYY-MM]   positions: [{id, start, end|"present", quote_verified?}]
--as-of defaults to the current month (printed in the output as "as_of"). Excluded as unknown: year-only or unparseable dates, end before start, a start or end AFTER as-of,
and any position that carries a quote_verified field that is not exactly true.   exit 0 | 2 bad input"""
import datetime, json, re, sys
GAP_MONTHS = 6

def parse_month(v):
    m = re.match(r"^\s*(\d{4})\s*[-./]\s*(\d{1,2})\s*$", str(v or ""))
    if not m: return None
    y, mo = int(m[1]), int(m[2])
    return y * 12 + mo - 1 if 1950 <= y <= 2100 and 1 <= mo <= 12 else None     # year-only or unparseable => unknown

def month_label(n): return f"{n // 12:04d}-{n % 12 + 1:02d}"      # month index -> "YYYY-MM"

def is_present(v): return bool(re.match(r"^(present|current|now|ongoing)$", str(v or "").strip(), re.I))

def union(spans):
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + 1: out[-1][1] = max(out[-1][1], b)       # overlapping or back-to-back
        else: out.append([a, b])
    return out

def facts(positions, as_of):
    spans, unknown = [], []
    for p in positions:
        s = parse_month(p.get("start")); e = as_of if is_present(p.get("end")) else parse_month(p.get("end"))
        if ("quote_verified" in p and p["quote_verified"] is not True) or s is None or e is None or e < s or s > as_of or e > as_of: unknown.append(p.get("id"))
        else: spans.append((s, e))
    merged = union(spans); gaps = []
    for i in range(1, len(merged)):
        m = merged[i][0] - merged[i-1][1] - 1
        if m >= GAP_MONTHS: gaps.append({"after": month_label(merged[i-1][1]), "after_month": merged[i-1][1], "months": m})
    return {"total_months": sum(b - a + 1 for a, b in merged), "gaps": gaps, "unknown": unknown}

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    if "--as-of" in sys.argv:
        i = sys.argv.index("--as-of"); asof = parse_month(sys.argv[i + 1]) if i + 1 < len(sys.argv) else None
        if asof is None: print("bad input: --as-of needs a value like 2026-01"); sys.exit(2)
    else:
        now = datetime.date.today(); asof = now.year * 12 + now.month - 1
    try:
        pos = json.load(open(sys.argv[1], encoding="utf-8"))
        assert isinstance(pos, list) and pos and all(isinstance(p, dict) for p in pos)
    except (OSError, ValueError, AssertionError) as e: print(f"bad input: positions must be a non-empty JSON list of objects ({type(e).__name__})"); sys.exit(2)
    out = facts(pos, asof); out["as_of"] = month_label(asof)
    print(json.dumps(out, indent=1))
