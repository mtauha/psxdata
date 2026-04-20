---
title: psxdata -- Free PSX Data for Python
description: Free open-source Python library for Pakistan Stock Exchange (PSX) data -- KSE-100 historical prices, live trading board, sectors, indices, stock screener.
---

# psxdata -- Free KSE-100 & PSX Historical Data for Python

Open-source Python library to download free PSX stock data — historical prices, live trading board, KSE-100 indices, sector summaries, and more.

```bash
pip install psxdata
```

```python
import psxdata

# Download ENGRO historical prices
df = psxdata.stocks("ENGRO", start="2025-01-01", end="2025-12-31")
print(df.head())
#        date    open    high     low   close   volume
# 0  2025-01-02  ...     ...     ...    ...      ...
```

## Features

| Feature | Description |
| --- | --- |
| **Historical Data** | OHLCV prices for any PSX-listed stock, all history in one call |
| **Live Snapshots** | Point-in-time trading board data via screener |
| **KSE-100 & Indices** | All 18 PSX indices with constituent weights |
| **Sector Summary** | 37 sector breakdowns with advance/decline counts |
| **Stock Screener** | Filter all ~1,000 listed symbols |
| **Disk Cache** | Parquet-backed local cache — no repeated downloads |

## Why psxdata?

- **Free.** No API key. No rate-limit paywall. Scrapes the public PSX website directly.
- **pandas-native.** Every function returns a `DataFrame` ready for analysis.
- **No browser required.** Pure `requests` + `BeautifulSoup` — fast and dependency-light.
- **Cached.** Historical data never re-downloads. Today's data refreshes every 15 minutes.

## Install

Requires Python 3.11+.

```bash
pip install psxdata
```

## Quick Example

```python
import psxdata

# Historical prices
df = psxdata.stocks("LUCK", start="2024-01-01")

# All KSE-100 tickers
kse100 = psxdata.tickers(index="KSE100")

# Sector summary
sectors = psxdata.sectors()

# Index constituents
kse_df = psxdata.indices("KSE100")
```

Continue to [Getting Started](getting-started.md) for a full walkthrough.
