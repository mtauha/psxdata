---
title: Client & Core Functions
description: API reference for PSXClient and all psxdata module-level functions.
---

# Client & Core Functions

All public functions are available at the module level — no instantiation needed:

```python
import psxdata

df = psxdata.stocks("ENGRO")
```

For advanced use (custom cache directory, multiple clients), instantiate `PSXClient` directly.

## PSXClient

::: psxdata.client.PSXClient

## Module-level functions

These wrap a lazy shared `PSXClient` instance. They are the recommended entry point for most users.

::: psxdata.client.stocks

::: psxdata.client.quote

::: psxdata.client.tickers

::: psxdata.client.symbols

::: psxdata.client.indices

::: psxdata.client.sectors

::: psxdata.client.fundamentals

::: psxdata.client.debt_market

::: psxdata.client.eligible_scrips
