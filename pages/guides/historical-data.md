---
title: Download PSX Historical Stock Prices with Python
description: Download historical OHLCV prices for any PSX-listed stock using psxdata. Works with pandas out of the box.
---

# Download PSX Historical Stock Prices with Python

psxdata returns complete OHLCV history for any PSX-listed stock in a single call.

## Basic usage

```python
import psxdata

df = psxdata.stocks("ENGRO", start="2025-01-01", end="2025-12-31")
print(df.head())
```

Output:

```
        date    open    high     low   close    volume  is_anomaly
0 2025-01-02  286.90  293.50  285.00  291.00   1234567       False
1 2025-01-03  291.00  295.00  289.00  293.50    987654       False
...
```

## Date filtering

`start` and `end` accept `str` (ISO format), `datetime.date`, or `None`.

```python
# Last 90 days
from datetime import date, timedelta

end = date.today()
start = end - timedelta(days=90)
df = psxdata.stocks("LUCK", start=start, end=end)
```

## Compute returns

```python
import psxdata

df = psxdata.stocks("HBL", start="2024-01-01")
df = df.sort_values("date").reset_index(drop=True)

df["daily_return"] = df["close"].pct_change()
df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1

print(df[["date", "close", "daily_return", "cumulative_return"]].tail())
```

## Save to CSV or Excel

```python
import psxdata

df = psxdata.stocks("ENGRO", start="2021-01-01")
df.to_csv("engro_history.csv", index=False)
df.to_excel("engro_history.xlsx", index=False)
```

## Fetch multiple stocks

```python
import psxdata
import pandas as pd

tickers = ["ENGRO", "LUCK", "HBL"]
frames = {t: psxdata.stocks(t, start="2025-01-01") for t in tickers}

# Build a close-price matrix
close = pd.DataFrame({t: df.set_index("date")["close"] for t, df in frames.items()})
print(close.tail())
```

## Bypass cache

```python
# Always fetch fresh from PSX (slower)
df = psxdata.stocks("ENGRO", cache=False)
```

## See also

- [`PSXClient.stocks()`](../api/client.md) — full parameter reference
- [Stock Screener guide](stock-screener.md) — find which stocks to analyse
