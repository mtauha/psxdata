"""Unit tests for psxdata.scrapers.token - network-free."""
from pathlib import Path

import pytest

from psxdata.scrapers.token import extract_token

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIXTURE_TOKEN = "JPlHf0jIKj_s7l-A_KlM4gGDz651a_5sknoT4WozNjM"


class TestExtractToken:
    def test_extracts_token_from_fixture(self):
        html = (FIXTURES / "home_with_token.html").read_text(encoding="utf-8")
        assert extract_token(html) == FIXTURE_TOKEN

    def test_extract_token_tolerates_whitespace_and_newlines(self):
        html = (
            "<script>\n  window.__ps  =  {\n  \"lc\": \"en\",\n"
            f"  \"_k\": \"{FIXTURE_TOKEN}\"\n}} ;\n</script>"
        )
        assert extract_token(html) == FIXTURE_TOKEN

    def test_extract_token_without_semicolon(self):
        html = f'<script>window.__ps = {{"_k":"{FIXTURE_TOKEN}"}}</script>'
        assert extract_token(html) == FIXTURE_TOKEN

    def test_returns_none_when_script_missing(self):
        assert extract_token("<html><head></head><body></body></html>") is None

    def test_returns_none_when_k_missing(self):
        assert extract_token('<script>window.__ps = {"lc":"en"};</script>') is None

    def test_returns_none_on_malformed_json(self):
        assert extract_token("<script>window.__ps = {_k: broken};</script>") is None

    @pytest.mark.parametrize("bad", ["short", "has spaces in it here!!", "", "x" * 15])
    def test_returns_none_when_token_fails_format_check(self, bad):
        assert extract_token(f'<script>window.__ps = {{"_k":"{bad}"}};</script>') is None

    def test_returns_none_when_k_not_a_string(self):
        html = '<script>window.__ps = {"_k": 12345678901234567890};</script>'
        assert extract_token(html) is None
