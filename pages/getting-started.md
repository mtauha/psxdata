---
title: Getting Started
description: Install psxdata and fetch your first PSX stock data in under 5 minutes.
---

# Getting Started

## Installation

Requires Python 3.11+.

```bash
pip install psxdata
```

To install inside a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
pip install psxdata
```

## Your first script

Fetch five years of ENGRO historical prices:

```python
import psxdata

df = psxdata.stocks("ENGRO", start="2021-01-01", end="2025-12-31")
print(df.shape)       # (rows, 7)
print(df.dtypes)
print(df.head())
```

Expected output:

```
(1234, 7)
date         datetime64[ns]
open                float64
high                float64
low                 float64
close               float64
volume                int64
is_anomaly             bool
dtype: object

        date    open    high     low   close    volume  is_anomaly
0 2021-01-04  286.90  293.50  285.00  291.00   1200000       False
...
```

## Caching

psxdata caches all data to `~/.psxdata/cache/` using parquet format. Historical data (before today) never expires. Today's rows refresh every 15 minutes.

To bypass the cache:

```python
df = psxdata.stocks("ENGRO", cache=False)
```

## Next steps

- [Historical Stock Prices guide](guides/historical-data.md) — full walkthrough with pandas analysis
- [Stock Screener guide](guides/stock-screener.md) — filter all listed stocks
- [API Reference](api/client.md) — complete function signatures and parameters
