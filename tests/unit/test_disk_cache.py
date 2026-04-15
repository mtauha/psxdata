"""Unit tests for psxdata/cache/disk_cache.py."""
import time
from datetime import date

import pandas as pd
import pytest

from psxdata.cache.disk_cache import DiskCache


@pytest.fixture
def cache(tmp_path):
    """DiskCache instance using a temp directory — isolated per test."""
    return DiskCache(cache_dir=str(tmp_path / "test_cache"))


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "open": [100.0, 101.0, 102.0],
        "close": [105.0, 106.0, 107.0],
        "volume": [1000, 2000, 3000],
    })


class TestDiskCacheMissAndHit:
    def test_cache_miss_returns_none(self, cache):
        assert cache.get("ENGRO_2024-01-01_2024-12-31") is None

    def test_write_then_read_returns_equal_df(self, cache, sample_df):
        key = "ENGRO_2024-01-01_2024-01-03"
        cache.set(key, sample_df)
        result = cache.get(key)
        assert result is not None
        pd.testing.assert_frame_equal(result, sample_df)

    def test_parquet_round_trip_preserves_dtypes(self, cache, sample_df):
        key = "DTYPE_TEST"
        cache.set(key, sample_df)
        result = cache.get(key)
        assert result["date"].dtype == sample_df["date"].dtype
        assert result["open"].dtype == sample_df["open"].dtype
        assert result["volume"].dtype == sample_df["volume"].dtype

    def test_delete_removes_entry(self, cache, sample_df):
        key = "TO_DELETE"
        cache.set(key, sample_df)
        cache.delete(key)
        assert cache.get(key) is None

    def test_clear_removes_all_entries(self, cache, sample_df):
        cache.set("KEY1", sample_df)
        cache.set("KEY2", sample_df)
        cache.clear()
        assert cache.get("KEY1") is None
        assert cache.get("KEY2") is None


class TestDiskCacheTTL:
    def test_historical_data_never_expires(self, cache, sample_df):
        cache.set("HIST", sample_df, ttl=None)
        result = cache.get("HIST")
        assert result is not None

    def test_today_data_expires_after_ttl(self, cache, sample_df):
        cache.set("TODAY", sample_df, ttl=1)
        assert cache.get("TODAY") is not None
        time.sleep(1.1)
        assert cache.get("TODAY") is None


class TestDiskCacheDict:
    @pytest.fixture
    def tables(self):
        return {
            "table_0": pd.DataFrame({"security_name": ["Bond A"], "value": [1.0]}),
            "table_1": pd.DataFrame({"security_name": ["Bond B"], "value": [2.0]}),
        }

    def test_dict_miss_returns_none(self, cache):
        assert cache.get_dict("debt_market_all") is None

    def test_dict_write_then_read(self, cache, tables):
        cache.set_dict("debt_market_all", tables)
        result = cache.get_dict("debt_market_all")
        assert result is not None
        assert set(result.keys()) == {"table_0", "table_1"}
        pd.testing.assert_frame_equal(result["table_0"], tables["table_0"])
        pd.testing.assert_frame_equal(result["table_1"], tables["table_1"])

    def test_dict_partial_hit_returns_none(self, cache, tables):
        """If any table entry expires, get_dict returns None (full miss)."""
        cache.set_dict("partial_key", tables, ttl=1)
        assert cache.get_dict("partial_key") is not None
        # Manually delete one table entry to simulate partial expiry
        cache.delete("partial_key__table_1")
        assert cache.get_dict("partial_key") is None

    def test_dict_ttl_expires(self, cache, tables):
        cache.set_dict("ttl_key", tables, ttl=1)
        assert cache.get_dict("ttl_key") is not None
        time.sleep(1.1)
        assert cache.get_dict("ttl_key") is None


class TestDiskCacheKeyConvention:
    def test_standard_key_format(self, cache, sample_df):
        """Demonstrate the standard caller key convention."""
        symbol = "engro"
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        key = f"{symbol.upper()}_{start.isoformat()}_{end.isoformat()}"
        assert key == "ENGRO_2024-01-01_2024-12-31"
        cache.set(key, sample_df)
        assert cache.get(key) is not None
        # Different case misses — key is caller's responsibility
        assert cache.get("engro_2024-01-01_2024-12-31") is None
