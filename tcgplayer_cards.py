#!/usr/bin/env python3
"""Collect TCGplayer card listings and print a seller-comparison table.

Requires: pip install playwright rich && playwright install chromium
Use only at a rate permitted by TCGplayer's Terms of Service and robots.txt.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console
from rich.table import Table

BASE = "https://www.tcgplayer.com"
MONEY = re.compile(r"\$\s*([0-9]+(?:,[0-9]{3})*(?:\.\d{2})?)")

@dataclass
class Listing:
    card: str
    condition: str
    price: float
    seller: str
    url: str


def card_links(page, search_url: str, debug_dir: str | None = None, wait_seconds: float = 5) -> list[tuple[str, str]]:
    page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(int(wait_seconds * 1000))
    if debug_dir:
        from pathlib import Path
        path = Path(debug_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "search-page.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(path / "search-page.png"), full_page=True)
    # Product links have /product/<numeric id>/...; de-duplicate while retaining order.
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in page.locator('a[href*="/product/"]').all():
        href = a.get_attribute("href")
        name = (a.inner_text() or "").strip().replace("\n", " ")
        if not href:
            continue
        href = urljoin(BASE, href.split("?")[0])
        if href not in seen:
            seen.add(href)
            found.append((name or href.rsplit("/", 1)[-1], href))
    return found


def text(locator) -> str:
    try:
        return " ".join((locator.inner_text() or "").split())
    except Exception:
        return ""


def listings_for(page, card: str, url: str, max_per_card: int, wait_seconds: float) -> list[Listing]:
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(int(wait_seconds * 1000))
    try:
        page.wait_for_selector(
            ".product-details__listings-results .listing-item",
            timeout=15_000,
        )
    except PlaywrightTimeoutError:
        # The product can exist without available listings. Continue so the
        # caller still gets diagnostics and an empty result rather than failing.
        pass
    # The selectors intentionally include stable semantic attributes and broad fallbacks;
    # TCGplayer changes its CSS classes periodically.
    for selector in [
        'button:has-text("Show More")',
        'button:has-text("Load More")',
    ]:
        try:
            for _ in range(3):
                page.locator(selector).first.click(timeout=800)
                page.wait_for_timeout(500)
        except Exception:
            pass

    # Current TCGplayer markup uses .listing-item inside
    # .product-details__listings-results. Keep the older fallbacks for compatibility.
    rows = page.locator(
        '.product-details__listings-results .listing-item, '
        '[data-testid*="listing"], [class*="listing-row"], [class*="product-listing"]'
    )
    result: list[Listing] = []
    for i in range(min(rows.count(), max_per_card * 3)):
        row = rows.nth(i)
        blob = text(row)
        prices = MONEY.findall(blob)
        if not prices:
            continue
        # Prefer explicit elements, then the first dollar amount in the row.
        condition = ""
        for sel in ['.condition', '[class*="condition"]', '[data-testid*="condition"]']:
            condition = text(row.locator(sel).first)
            if condition:
                break
        seller = ""
        for sel in ['.seller', '[class*="seller"]', '[data-testid*="seller"]', 'a[href*="seller"]']:
            seller = text(row.locator(sel).first)
            if seller:
                break
        if not seller:
            # Usually seller text follows “Seller:” in the rendered row.
            match = re.search(r"Seller:\s*([^$]+?)(?:\s{2,}|\s+\$)", blob, re.I)
            seller = match.group(1).strip() if match else "Unknown"
        try:
            price = float(prices[0].replace(",", ""))
        except ValueError:
            continue
        result.append(Listing(card, condition or "Unknown", price, seller, url))
        if len(result) >= max_per_card:
            break
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("search_url", help="TCGplayer search-results URL")
    ap.add_argument("--max-cards", type=int, default=0, help="0 means all cards on the page")
    ap.add_argument("--listings-per-card", type=int, default=5)
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between product pages")
    ap.add_argument("--csv", metavar="FILE", help="also write raw listings to CSV")
    ap.add_argument("--debug-dir", metavar="DIR", help="save rendered search HTML and screenshot")
    ap.add_argument("--headed", action="store_true", help="show Chromium instead of running headlessly")
    ap.add_argument("--profile", default="browser-profile", metavar="DIR", help="persistent browser profile directory")
    ap.add_argument("--wait", type=float, default=10, help="seconds to wait for dynamic results")
    args = ap.parse_args()
    console = Console()
    all_listings: list[Listing] = []
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            args.profile,
            headless=not args.headed,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("console", lambda message: console.print(
            f"[dim]BROWSER {message.type}: {message.text}[/dim]"))
        page.on("pageerror", lambda error: console.print(
            f"[yellow]PAGE ERROR: {error}[/yellow]"))
        page.on("requestfailed", lambda request: console.print(
            f"[yellow]REQUEST FAILED: {request.url} - {request.failure}[/yellow]"))
        page.on("response", lambda response: console.print(
            f"[yellow]HTTP {response.status}: {response.url}[/yellow]"
        ) if response.status >= 400 else None)
        try:
            links = card_links(page, args.search_url, args.debug_dir, args.wait)
            if args.max_cards:
                links = links[:args.max_cards]
            console.print(f"Found [bold]{len(links)}[/bold] card products")
            for n, (name, url) in enumerate(links, 1):
                try:
                    rows = listings_for(page, name, url, args.listings_per_card, args.wait)
                    all_listings.extend(rows)
                    console.print(f"[{n}/{len(links)}] {name}: {len(rows)} listings")
                except PlaywrightTimeoutError:
                    console.print(f"[yellow]Skipped (timeout):[/yellow] {name}")
                time.sleep(args.delay)
        finally:
            context.close()

    table = Table(title="TCGplayer listings")
    for col in ("Card", "Condition", "Price", "Seller"):
        table.add_column(col)
    for x in sorted(all_listings, key=lambda z: (z.card.lower(), z.price)):
        table.add_row(x.card, x.condition, f"${x.price:,.2f}", x.seller)
    console.print(table)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["card", "condition", "price", "seller", "url"])
            writer.writeheader()
            writer.writerows(asdict(x) for x in all_listings)
        console.print(f"Wrote {args.csv}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
