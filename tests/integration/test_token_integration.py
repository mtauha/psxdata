"""Integration tests for the PSX X-Req-Id token flow - hits real PSX. Requires network."""
import pytest

from psxdata.scrapers.historical import HistoricalScraper
from psxdata.scrapers.symbols import SymbolsScraper
from psxdata.scrapers.token import _TOKEN_RE, TokenProvider, get_default_provider

pytestmark = pytest.mark.integration


class TestTokenIntegration:
    def test_default_provider_is_real_in_integration(self):
        # Guards against the conftest offline stub leaking into live tests.
        assert type(get_default_provider()) is TokenProvider

    def test_live_token_has_expected_format(self):
        token = TokenProvider().get_token()
        assert token is not None
        assert _TOKEN_RE.match(token)

    def test_symbols_endpoint_returns_data_with_token(self):
        df = SymbolsScraper().fetch()
        assert len(df) > 900

    def test_historical_endpoint_returns_data_with_token(self):
        df = HistoricalScraper().fetch("HBL")
        assert len(df) > 100
