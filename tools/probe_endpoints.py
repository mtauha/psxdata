#!/usr/bin/env python3
"""Probe all PSX AJAX endpoints — schema extraction, diffing, and report generation.

Usage:
    python tools/probe_endpoints.py                  # probe all, write PSX_ENDPOINTS.md
    python tools/probe_endpoints.py --save-baseline  # save schema to endpoint_schema.json
    python tools/probe_endpoints.py --diff           # compare live vs baseline, exit 1 on drift
    python tools/probe_endpoints.py --endpoint historical  # probe one endpoint
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DOCS_DIR = Path(__file__).parent.parent / "docs"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
BASELINE_PATH = FIXTURES_DIR / "endpoint_schema.json"

BASE_URL = "https://dps.psx.com.pk"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://dps.psx.com.pk/",
    "X-Requested-With": "XMLHttpRequest",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


ENDPOINTS = [
    {"name": "historical", "url": "/historical", "method": "POST",
     "data": {"symbol": "ENGRO", "date_from": "2010-01-01", "date_to": "2025-12-31"},
     "response_type": "html"},
    {"name": "screener", "url": "/screener", "method": "GET",
     "data": None, "response_type": "html"},
    {"name": "trading_panel", "url": "/trading-panel", "method": "GET",
     "data": None, "response_type": "html"},
    {"name": "debt_market", "url": "/debt-market", "method": "GET",
     "data": None, "response_type": "html"},
    {"name": "eligible_scrips", "url": "/eligible-scrips", "method": "GET",
     "data": None, "response_type": "html"},
    # AJAX endpoints
    {"name": "trading_board_reg_main", "url": "/trading-board/REG/main",
     "method": "GET", "data": None, "response_type": "html"},
    {"name": "trading_board_reg_gem", "url": "/trading-board/REG/gem",
     "method": "GET", "data": None, "response_type": "html"},
    {"name": "trading_board_bnb_bnb", "url": "/trading-board/BNB/bnb",
     "method": "GET", "data": None, "response_type": "html"},
    {"name": "symbols", "url": "/symbols", "method": "GET",
     "data": None, "response_type": "json"},
    {"name": "sector_summary", "url": "/sector-summary/sectorwise",
     "method": "GET", "data": None, "response_type": "html"},
    {"name": "financial_reports", "url": "/financial-reports-list",
     "method": "GET", "data": None, "response_type": "html"},
    {"name": "indices_kse100", "url": "/indices/KSE100", "method": "GET",
     "data": None, "response_type": "html"},
    {"name": "indices_allshr", "url": "/indices/ALLSHR", "method": "GET",
     "data": None, "response_type": "html"},
]


def probe_endpoint(ep: dict, session: requests.Session) -> dict:
    """Probe one endpoint and return schema info."""
    url = f"{BASE_URL}{ep['url']}"
    t0 = time.monotonic()
    try:
        if ep["method"] == "POST":
            resp = session.post(url, data=ep["data"], timeout=30)
        else:
            resp = session.get(url, timeout=30)
        elapsed = round(time.monotonic() - t0, 2)
    except Exception as exc:
        return {"name": ep["name"], "error": str(exc)}

    result = {
        "name": ep["name"],
        "url": ep["url"],
        "method": ep["method"],
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "size_bytes": len(resp.content),
        "response_time_s": elapsed,
    }

    if ep["response_type"] == "json":
        try:
            data = resp.json()
            if isinstance(data, list):
                result["row_count"] = len(data)
                result["json_keys"] = sorted(data[0].keys()) if data else []
            elif isinstance(data, dict):
                result["json_keys"] = sorted(data.keys())
        except Exception:
            result["json_keys"] = []
    else:
        soup = BeautifulSoup(resp.text, "lxml")
        tables = soup.find_all("table")
        result["table_count"] = len(tables)
        if tables:
            first = tables[0]
            headers = [th.get_text(strip=True) for th in first.find_all("th")]
            rows = first.find_all("tr")
            data_rows = [
                r for r in rows if r.find_all("td")
            ]
            sample = []
            if data_rows:
                sample = [
                    td.get_text(strip=True)
                    for td in data_rows[0].find_all("td")
                ]
            result["headers"] = headers
            result["row_count"] = len(data_rows)
            result["sample_row"] = sample[:8]

    return result


def save_baseline(results: list[dict]) -> Path:
    """Save probe results as schema baseline."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    baseline = {
        "probed_at": str(date.today()),
        "endpoints": {r["name"]: r for r in results if "error" not in r},
    }
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return BASELINE_PATH


def load_baseline() -> dict:
    """Load saved baseline."""
    if not BASELINE_PATH.exists():
        print(f"No baseline found at {BASELINE_PATH}")
        print("Run: python tools/probe_endpoints.py --save-baseline")
        sys.exit(1)
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def diff_schemas(results: list[dict], baseline: dict) -> list[str]:
    """Compare live results against baseline, return list of drift messages."""
    diffs = []
    base_eps = baseline.get("endpoints", {})

    info = []  # informational only — new endpoints not in baseline
    for r in results:
        name = r["name"]
        if "error" in r:
            diffs.append(f"! {name}: probe failed — {r['error']}")
            continue
        if name not in base_eps:
            info.append(f"+ {name}: NEW endpoint (not in baseline — run --save-baseline)")
            continue

        old = base_eps[name]

        # Header drift
        old_h = set(old.get("headers", old.get("json_keys", [])))
        new_h = set(r.get("headers", r.get("json_keys", [])))
        for h in new_h - old_h:
            diffs.append(f"+ {name}: NEW COLUMN '{h}'")
        for h in old_h - new_h:
            diffs.append(f"- {name}: REMOVED COLUMN '{h}'")

        # Row count drift (> 50% change)
        old_count = old.get("row_count", 0)
        new_count = r.get("row_count", 0)
        if old_count == 0 and new_count > 0:
            diffs.append(f"! {name}: ROW COUNT was 0, now {new_count} (table appeared)")
        elif old_count > 0:
            pct = abs(new_count - old_count) / old_count
            if pct > 0.5:
                diffs.append(
                    f"! {name}: ROW COUNT {old_count} -> {new_count} "
                    f"({pct:.0%} change)"
                )

        # Status code change
        if old.get("status") != r.get("status"):
            diffs.append(
                f"! {name}: STATUS {old.get('status')} -> {r.get('status')}"
            )

    # Check for removed endpoints
    live_names = {r["name"] for r in results}
    for name in base_eps:
        if name not in live_names:
            diffs.append(f"- {name}: MISSING from probe (was in baseline)")

    if info:
        print("  Info (not drift):")
        for msg in info:
            print(f"    {msg}")

    return diffs


def write_report(results: list[dict]) -> Path:
    """Write docs/PSX_ENDPOINTS.md from probe results."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOCS_DIR / "PSX_ENDPOINTS.md"

    lines = [
        "# PSX Endpoints — Live Probe Results",
        "",
        f"**Last probed:** {date.today()}",
        "**Probe script:** `python tools/probe_endpoints.py`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Endpoint | Method | Status | Tables | Rows | Time |",
        "|---|---|---|---|---|---|",
    ]

    for r in results:
        if "error" in r:
            lines.append(f"| {r['name']} | — | ERROR | — | — | — |")
            continue
        tables = r.get("table_count", "—")
        rows = r.get("row_count", "—")
        lines.append(
            f"| `{r['url']}` | {r['method']} | {r['status']} "
            f"| {tables} | {rows} | {r['response_time_s']}s |"
        )

    lines.extend(["", "---", ""])

    for r in results:
        if "error" in r:
            lines.extend([f"## {r['name']}", "", f"**Error:** {r['error']}", "", "---", ""])
            continue
        lines.append(f"## {r['name']}")
        lines.append("")
        lines.append(f"**URL:** `{BASE_URL}{r['url']}`")
        lines.append(f"**Method:** {r['method']}")
        lines.append(f"**Status:** {r['status']}")
        lines.append(f"**Size:** {r['size_bytes']:,} bytes")
        lines.append(f"**Response time:** {r['response_time_s']}s")
        headers = r.get("headers", r.get("json_keys", []))
        if headers:
            lines.append(f"**Columns:** `{', '.join(headers)}`")
        rows = r.get("row_count")
        if rows is not None:
            lines.append(f"**Row count:** {rows}")
        sample = r.get("sample_row", [])
        if sample:
            lines.append(f"**Sample row:** `{' | '.join(sample)}`")
        lines.extend(["", "---", ""])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe PSX AJAX endpoints"
    )
    parser.add_argument("--endpoint", help="Probe only this endpoint name")
    parser.add_argument(
        "--save-baseline", action="store_true",
        help="Save schema baseline to tests/fixtures/endpoint_schema.json",
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="Compare live schema against baseline, exit 1 on drift",
    )
    args = parser.parse_args()

    if args.save_baseline and args.diff:
        print("Error: --save-baseline and --diff are mutually exclusive.", file=sys.stderr)
        print("Run --save-baseline first, then --diff separately.", file=sys.stderr)
        sys.exit(2)

    targets = ENDPOINTS
    if args.endpoint:
        targets = [e for e in ENDPOINTS if e["name"] == args.endpoint]
        if not targets:
            names = [e["name"] for e in ENDPOINTS]
            print(f"Unknown: {args.endpoint}. Valid: {names}")
            sys.exit(1)

    session = _session()
    results = []

    print(f"Probing {len(targets)} endpoint(s)...")
    for ep in targets:
        print(f"  {ep['name']} ({ep['method']} {ep['url']}) ...", end=" ", flush=True)
        result = probe_endpoint(ep, session)
        results.append(result)
        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print(f"OK ({result['response_time_s']}s)")

    if args.save_baseline:
        path = save_baseline(results)
        print(f"\nBaseline saved: {path}")

    if args.diff:
        baseline = load_baseline()
        drifts = diff_schemas(results, baseline)
        if drifts:
            print(f"\n{len(drifts)} schema drift(s) detected:")
            for d in drifts:
                print(f"  {d}")
            sys.exit(1)
        else:
            print("\nNo schema drift detected.")
            sys.exit(0)
    else:
        report = write_report(results)
        print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
