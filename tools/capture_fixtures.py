#!/usr/bin/env python3
"""
PSX HTML fixture capture tool.

Captures static HTML snapshots of PSX endpoints for use in unit tests.
Run during Phase 0 or any time PSX changes a page structure.

Usage:
    python tools/capture_fixtures.py                           # capture all fixtures
    python tools/capture_fixtures.py --fixture trading_panel   # capture one fixture
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"

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

END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=30)


def stamp(url: str, html: str) -> str:
    """Prepend metadata comment to captured HTML."""
    today = date.today()
    comment = (
        f"<!-- Captured: {today} | Source: {url} | Phase 0 probe -->\n"
        "<!-- If unit tests pass but integration tests fail, this fixture may be stale."
        " Re-capture with: -->\n"
        "<!-- python tools/capture_fixtures.py -->\n"
    )
    return comment + html


def capture_historical_engro() -> tuple[Path, int]:
    """Capture /historical ENGRO response via requests POST."""
    url = f"{BASE_URL}/historical"
    session = requests.Session()
    session.headers.update(HEADERS)
    resp = session.post(
        url,
        data={"symbol": "ENGRO", "start": str(START_DATE), "end": str(END_DATE)},
        timeout=30,
    )
    resp.raise_for_status()
    html = stamp(url, resp.text)
    out = FIXTURES_DIR / "historical_engro.html"
    out.write_text(html, encoding="utf-8")
    return out, len(html.encode())


def capture_playwright_page(endpoint: str, filename: str) -> tuple[Path, int]:
    """Capture a JS-rendered PSX page via Playwright."""
    url = f"{BASE_URL}/{endpoint}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers=HEADERS)
        page.goto(url, timeout=30000, wait_until="networkidle")
        html = page.content()
        browser.close()
    stamped = stamp(url, html)
    out = FIXTURES_DIR / filename
    out.write_text(stamped, encoding="utf-8")
    return out, len(stamped.encode())


FIXTURES = {
    "historical_engro": {
        "description": "/historical ENGRO (requests POST)",
        "fn": lambda: capture_historical_engro(),
    },
    "trading_panel": {
        "description": "/trading-panel (Playwright JS-rendered)",
        "fn": lambda: capture_playwright_page("trading-panel", "trading_panel.html"),
    },
    "screener": {
        "description": "/screener (Playwright JS-rendered)",
        "fn": lambda: capture_playwright_page("screener", "screener.html"),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture PSX HTML fixtures for unit tests")
    parser.add_argument(
        "--fixture",
        choices=list(FIXTURES.keys()),
        help="Capture only this fixture",
    )
    args = parser.parse_args()

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    targets = {args.fixture: FIXTURES[args.fixture]} if args.fixture else FIXTURES
    failed = False

    for name, spec in targets.items():
        print(f"  Capturing {name} ({spec['description']}) ...", end=" ", flush=True)
        try:
            path, size = spec["fn"]()
            print(f"done — {path} ({size:,} bytes)")
        except Exception as exc:
            print(f"FAILED: {exc}")
            failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
