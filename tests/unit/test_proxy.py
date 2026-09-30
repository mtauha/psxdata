"""Unit tests for psxdata/proxy.py — validation, normalisation, redaction (#162)."""
from __future__ import annotations

import pytest

from psxdata import proxy as proxy_module
from psxdata.proxy import describe_proxies, normalize_proxy, redact_text, redact_url


@pytest.fixture
def socks_installed(monkeypatch):
    monkeypatch.setattr(proxy_module.importlib.util, "find_spec", lambda name: object())


@pytest.fixture
def socks_missing(monkeypatch):
    monkeypatch.setattr(proxy_module.importlib.util, "find_spec", lambda name: None)


class TestNormalizeProxy:
    def test_none_means_no_proxy(self):
        assert normalize_proxy(None) is None

    def test_string_applies_to_http_and_https(self):
        url = "http://user:pass@proxy.example.com:8080"
        assert normalize_proxy(url) == {"http": url, "https": url}

    def test_dict_is_copied(self):
        proxies = {"http": "http://p:8080", "https": "http://p:8443"}
        result = normalize_proxy(proxies)
        assert result == proxies
        assert result is not proxies

    @pytest.mark.parametrize("url", ["https://p:8443", "HTTP://p:8080", "http://[::1]:3128"])
    def test_accepts_http_and_https_schemes(self, url):
        assert normalize_proxy(url) == {"http": url, "https": url}

    @pytest.mark.parametrize("url", ["socks5://127.0.0.1:1080", "socks5h://u:p@host:1080"])
    def test_accepts_socks_when_pysocks_installed(self, socks_installed, url):
        assert normalize_proxy(url) == {"http": url, "https": url}

    def test_socks_without_pysocks_raises_import_error_with_hint(self, socks_missing):
        with pytest.raises(ImportError, match=r"psxdata\[socks\]"):
            normalize_proxy("socks5://127.0.0.1:1080")

    @pytest.mark.parametrize(
        "url", ["proxy.example.com:8080", "ftp://p:21", "", "http://", "http://p:notaport"]
    )
    def test_invalid_urls_raise_value_error(self, url):
        with pytest.raises(ValueError):
            normalize_proxy(url)

    def test_invalid_url_error_hides_credentials(self):
        with pytest.raises(ValueError) as excinfo:
            normalize_proxy("ftp://alice:s3cret@p:21")
        assert "s3cret" not in str(excinfo.value)
        assert "alice" not in str(excinfo.value)

    def test_empty_dict_raises(self):
        with pytest.raises(ValueError):
            normalize_proxy({})

    def test_non_string_dict_value_raises(self):
        with pytest.raises(TypeError):
            normalize_proxy({"http": 8080})  # type: ignore[dict-item]

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError):
            normalize_proxy(8080)  # type: ignore[arg-type]


class TestRedaction:
    def test_redact_url_hides_userinfo(self):
        assert redact_url("http://alice:s3cret@p:8080") == "http://***@p:8080"

    def test_redact_url_without_credentials_is_unchanged(self):
        assert redact_url("http://p:8080") == "http://p:8080"

    def test_describe_single_proxy(self):
        url = "http://alice:s3cret@p:8080"
        assert describe_proxies({"http": url, "https": url}) == "http://***@p:8080"

    def test_describe_per_scheme_proxies(self):
        desc = describe_proxies({"http": "http://a:b@p:8080", "https": "http://p:8443"})
        assert desc == "http=http://***@p:8080, https=http://p:8443"

    def test_redact_text_removes_url_userinfo_and_password(self):
        url = "http://alice:s%40cret@p:8080"
        text = f"failed via {url}; auth alice:s%40cret@p; password s@cret"
        redacted = redact_text(text, {"https": url})
        assert "s%40cret" not in redacted
        assert "s@cret" not in redacted
        assert "alice" not in redacted

    def test_redact_text_without_proxies_is_unchanged(self):
        assert redact_text("boom", None) == "boom"
