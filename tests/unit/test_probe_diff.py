"""Unit tests for tools/probe_endpoints.py::diff_schemas().

Issue #98: verifies drift detection logic against synthetic baseline/live pairs.
No network required — all inputs are constructed inline.
"""
import importlib.util
from pathlib import Path

# Import probe_endpoints as a module from tools/ without installing it
_probe_path = Path(__file__).parent.parent.parent / "tools" / "probe_endpoints.py"
_spec = importlib.util.spec_from_file_location("probe_endpoints", _probe_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
diff_schemas = _mod.diff_schemas


def _baseline(endpoints: dict) -> dict:
    """Build a minimal baseline dict matching save_baseline() output shape."""
    return {"probed_at": "2026-01-01", "endpoints": endpoints}


def _result(name: str, headers: list[str], row_count: int = 10, status: int = 200) -> dict:
    return {
        "name": name,
        "url": f"/{name}",
        "method": "GET",
        "status": status,
        "headers": headers,
        "row_count": row_count,
    }


class TestDiffSchemasNoChange:
    def test_identical_results_return_empty_list(self):
        base = _baseline({"ep": _result("ep", ["DATE", "OPEN", "CLOSE"], row_count=100)})
        live = [_result("ep", ["DATE", "OPEN", "CLOSE"], row_count=100)]
        diffs = diff_schemas(live, base)
        assert diffs == []

    def test_minor_row_count_change_not_flagged(self):
        """< 50% row count change must NOT be reported as drift."""
        base = _baseline({"ep": _result("ep", ["DATE"], row_count=100)})
        live = [_result("ep", ["DATE"], row_count=130)]  # 30% change
        diffs = diff_schemas(live, base)
        assert diffs == []


class TestDiffSchemasColumnDrift:
    def test_new_column_reported_with_plus_prefix(self):
        base = _baseline({"ep": _result("ep", ["DATE", "OPEN"])})
        live = [_result("ep", ["DATE", "OPEN", "NEW_COL"])]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("+")
        assert "NEW_COL" in diffs[0]

    def test_removed_column_reported_with_minus_prefix(self):
        base = _baseline({"ep": _result("ep", ["DATE", "OPEN", "CLOSE"])})
        live = [_result("ep", ["DATE", "OPEN"])]  # CLOSE removed
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("-")
        assert "CLOSE" in diffs[0]

    def test_renamed_column_reported_as_add_and_remove(self):
        """Rename = removed old + added new — two drift entries."""
        base = _baseline({"ep": _result("ep", ["OLD_COL"])})
        live = [_result("ep", ["NEW_COL"])]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 2
        prefixes = {d[0] for d in diffs}
        assert "+" in prefixes
        assert "-" in prefixes


class TestDiffSchemasRowCountDrift:
    def test_row_count_increase_over_50pct_flagged(self):
        base = _baseline({"ep": _result("ep", ["DATE"], row_count=100)})
        live = [_result("ep", ["DATE"], row_count=200)]  # 100% increase
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("!")
        assert "ROW COUNT" in diffs[0].upper() or "row" in diffs[0].lower()

    def test_row_count_drop_to_zero_from_nonzero_flagged(self):
        base = _baseline({"ep": _result("ep", ["DATE"], row_count=10)})
        live = [_result("ep", ["DATE"], row_count=0)]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("!")
        assert "row" in diffs[0].lower() or "ROW" in diffs[0]

    def test_zero_to_nonzero_row_count_flagged(self):
        base = _baseline({"ep": _result("ep", ["DATE"], row_count=0)})
        live = [_result("ep", ["DATE"], row_count=50)]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("!")
        assert "row" in diffs[0].lower() or "ROW" in diffs[0]


class TestDiffSchemasStatusDrift:
    def test_status_code_change_flagged(self):
        base = _baseline({"ep": _result("ep", ["DATE"], status=200)})
        live = [_result("ep", ["DATE"], status=301)]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert diffs[0].startswith("!")
        assert "301" in diffs[0] or "status" in diffs[0].lower()


class TestDiffSchemasEndpointPresence:
    def test_endpoint_missing_from_live_is_flagged(self):
        base = _baseline({
            "ep_a": _result("ep_a", ["DATE"]),
            "ep_b": _result("ep_b", ["DATE"]),
        })
        live = [_result("ep_a", ["DATE"])]  # ep_b gone
        diffs = diff_schemas(live, base)
        assert any("ep_b" in d for d in diffs)
        missing = [d for d in diffs if "ep_b" in d]
        assert missing[0].startswith("-")

    def test_probe_failure_in_live_is_flagged(self):
        base = _baseline({"ep": _result("ep", ["DATE"])})
        live = [{"name": "ep", "error": "Connection timeout"}]
        diffs = diff_schemas(live, base)
        assert len(diffs) == 1
        assert "ep" in diffs[0]

    def test_new_endpoint_not_in_baseline_not_in_diffs(self):
        """New endpoint in live but not in baseline goes to info only."""
        base = _baseline({"ep_a": _result("ep_a", ["DATE"])})
        live = [_result("ep_a", ["DATE"]), _result("ep_new", ["COL"])]
        diffs = diff_schemas(live, base)
        assert not any("ep_new" in d for d in diffs)
