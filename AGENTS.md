# Agent guidance

## Project overview

Carter is a small Python command-line utility that uses Playwright and Chromium to collect TCGplayer card product listings and compare listing condition, price, and seller. The primary entry point is `tcgplayer_cards.py`; `tcgplayer_product_urls.py` is a separate helper for collecting product-page URLs from search results.

## Working conventions

- Keep the project focused on its command-line tools; there is no web application or backend.
- Preserve existing CLI options and CSV column names unless the task explicitly calls for a change. The listing collector's CSV fields are `card`, `condition`, `price`, `seller`, and `url`.
- TCGplayer pages are rendered dynamically. When changing collection logic, account for missing elements and selector changes, and keep failures understandable rather than crashing the entire scan when practical.
- Keep scans conservative: respect TCGplayer's Terms of Service and `robots.txt`, use the configured delays, and do not add access-control or anti-bot circumvention.
- Keep Docker setup aligned with the Python dependencies and Playwright's Chromium installation.
- Update `README.md` when command-line behavior, options, setup, or output changes.

## Validation

- Install dependencies from `requirements.txt` and ensure Playwright's Chromium browser is installed before running the tools.
- For changes to CLI behavior, check `--help` and, where practical, run against a small or mocked page rather than performing a large live scan.
