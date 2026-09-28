# TCGplayer Card Listing Collector

A small Python utility that collects card listings from a TCGplayer search page and displays them in a table. It is intended to make it easier to compare card condition, price, and seller, and to identify sellers who carry multiple cards.

The collector uses Playwright because TCGplayer product and listing information is rendered dynamically in the browser.

> Use this tool responsibly and in accordance with TCGplayer's Terms of Service and `robots.txt`. Keep request rates low and avoid unnecessary repeated scans.

## Collected information

For each listing, the script attempts to collect:

- Card name
- Condition/quality
- Price
- Seller name
- Product page URL

Results are printed in a table and can optionally be saved as a CSV file.

## Option 1: Run with Docker

Docker is the recommended way to run the collector. The image installs Python, the Python packages, Chromium, and Chromium's Linux dependencies during the image build. The host machine only needs Docker.

### Build the image

From the project directory:

```bash
docker build -t tcgplayer-cards .
```

### Run a scan

```bash
docker run --rm tcgplayer-cards \
  "https://www.tcgplayer.com/search/pokemon/me-30th-celebration?productLineName=pokemon&setName=me-30th-celebration&productTypeName=Cards&page=1&view=grid"
```

### Limit the number of cards while testing

```bash
docker run --rm tcgplayer-cards \
  "YOUR_SEARCH_URL" \
  --max-cards 5
```

### Save results to CSV

Mount a local directory so the CSV remains available after the container exits:

```bash
mkdir -p output

docker run --rm \
  -v "$PWD/output:/app/output" \
  tcgplayer-cards \
  "YOUR_SEARCH_URL" \
  --csv /app/output/listings.csv
```

The resulting file will be written to `output/listings.csv` on the host.

## Option 2: Run locally with Python

Python 3.10 or newer is recommended.

### Install dependencies

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

On Linux, Playwright may also need system packages. This command installs them when supported:

```bash
python3 -m playwright install --with-deps chromium
```

### Run the script

```bash
python3 tcgplayer_cards.py \
  "YOUR_SEARCH_URL"
```

## Command-line options

```text
--max-cards N
```

Limit the number of product pages scanned. The default is `0`, which means all products found on the search-results page.

```text
--listings-per-card N
```

Maximum number of listings collected for each card. The default is `5`.

```text
--delay SECONDS
```

Delay between product pages. The default is `1.5` seconds. Increasing this value is recommended for larger scans.

```text
--csv FILE
```

Write the collected listings to a CSV file in addition to printing the table.

For example:

```bash
python3 tcgplayer_cards.py \
  "YOUR_SEARCH_URL" \
  --max-cards 10 \
  --listings-per-card 10 \
  --delay 3 \
  --csv listings.csv
```

## Understanding the output

The output contains one row per listing. Sort or filter the CSV by seller to see which sellers offer multiple cards. The script currently reports individual listing prices; it does not calculate shipping, taxes, cart totals, or the optimal multi-seller purchase combination.

## Troubleshooting

### No cards are found

The search page may not have finished loading, or TCGplayer may have changed its page structure. Confirm that the URL opens successfully in a regular browser and try again later.

### No listings are found

Listing markup and CSS selectors can change over time. The script relies on rendered page structure, so a TCGplayer redesign may require selector updates.

### Browser installation errors in Docker

Rebuild the image without using an old cached layer:

```bash
docker build --no-cache -t tcgplayer-cards .
```

### Scan is blocked or challenged

Do not attempt to bypass access controls. Reduce scan frequency, increase `--delay`, and check TCGplayer's current access policies.
