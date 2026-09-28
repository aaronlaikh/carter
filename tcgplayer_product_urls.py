#!/usr/bin/env python3
"""Collect product-page URLs from a TCGplayer search-results page."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.table import Table

BASE = "https://www.tcgplayer.com"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("search_url")
    parser.add_argument("--output", default="product-urls.csv", help="CSV output file")
    parser.add_argument("--profile", default="browser-profile")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--wait", type=float, default=15)
    parser.add_argument("--debug-dir", help="save rendered HTML and screenshot")
    parser.add_argument("--max-pages", type=int, default=100, help="maximum search pages to scan")
    args = parser.parse_args()
    console = Console()

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            args.profile,
            headless=not args.headed,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("console", lambda m: console.print(
            f"[dim]BROWSER {m.type}: {m.text}[/dim]"
        ) if not (m.type == "error" and "Failed to load resource" in m.text and "404" in m.text) else None)
        page.on("pageerror", lambda e: console.print(f"[yellow]PAGE ERROR: {e}[/yellow]"))
        page.on("requestfailed", lambda r: console.print(
            f"[yellow]REQUEST FAILED: {r.url} - {r.failure}[/yellow]"))
        page.on("response", lambda r: console.print(
            f"[yellow]HTTP {r.status}: {r.url}[/yellow]"
        ) if r.status >= 400 and "/c/promos/" not in r.url else None)
        try:
            results = []
            seen = set()
            original = urlsplit(args.search_url)
            query = dict(parse_qsl(original.query, keep_blank_values=True))
            start_page = int(query.get("page", "1"))

            for page_number in range(start_page, start_page + args.max_pages):
                query["page"] = str(page_number)
                search_url = urlunsplit((original.scheme, original.netloc, original.path, urlencode(query), original.fragment))
                console.print(f"Scanning search page {page_number}...")
                page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(int(args.wait * 1000))
                if args.debug_dir:
                    debug = Path(args.debug_dir)
                    debug.mkdir(parents=True, exist_ok=True)
                    (debug / f"search-page-{page_number}.html").write_text(page.content(), encoding="utf-8")
                    page.screenshot(path=str(debug / f"search-page-{page_number}.png"), full_page=True)

                before = len(seen)
                for link in page.locator('a[href*="/product/"]').all():
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    url = urljoin(BASE, href.split("?")[0])
                    if url in seen:
                        continue
                    seen.add(url)
                    name = " ".join((link.inner_text() or "").split())
                    if "code card" in name.lower():
                        continue
                    results.append((name, url))
                added = len(seen) - before
                console.print(f"  found {added} new product pages")
                if added == 0:
                    break
        finally:
            context.close()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["card", "product_url"])
        writer.writerows(results)

    table = Table(title="TCGplayer product pages")
    table.add_column("#", justify="right")
    table.add_column("Card")
    table.add_column("URL")
    for number, (name, url) in enumerate(results, 1):
        table.add_row(str(number), name or "(name not present)", url)
    console.print(f"Found {len(results)} product pages")
    console.print(table)
    console.print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
