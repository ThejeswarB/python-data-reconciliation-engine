import pandas as pd
import pytest

from reconciliation.engine import reconcile_dataframes


def sample_frames():
    source = pd.DataFrame(
        [
            {"id": 101, "name": "Rahul", "amount": 500},
            {"id": 102, "name": "Amit", "amount": 700},
            {"id": 103, "name": "Priya", "amount": 900},
        ]
    )
    target = pd.DataFrame(
        [
            {"id": 101, "name": "Rahul", "amount": 500},
            {"id": 102, "name": "Amit", "amount": 750},
            {"id": 104, "name": "Kiran", "amount": 600},
        ]
    )
    return source, target


def test_classifies_matching_mismatched_and_missing_records():
    source, target = sample_frames()
    result = reconcile_dataframes(source, target, keys=["id"], compare_columns=["name", "amount"])

    assert result.summary["matched_records"] == 1
    assert result.summary["mismatched_records"] == 1
    assert result.summary["source_only_records"] == 1
    assert result.summary["target_only_records"] == 1
    assert result.mismatched.iloc[0]["id"] == 102
    assert result.source_only.iloc[0]["id"] == 103
    assert result.target_only.iloc[0]["id"] == 104


def test_duplicate_keys_are_reported_and_excluded_from_one_to_one_matching():
    source = pd.DataFrame([{"id": 1, "value": "a"}, {"id": 1, "value": "b"}])
    target = pd.DataFrame([{"id": 1, "value": "a"}])
    result = reconcile_dataframes(source, target, keys=["id"], compare_columns=["value"])

    assert result.summary["source_duplicate_records"] == 2
    assert result.summary["target_duplicate_records"] == 0
    assert result.summary["matched_records"] == 0
    assert result.summary["source_only_records"] == 0
    assert result.summary["target_only_records"] == 0


def test_equal_null_comparison_values_are_treated_as_equal():
    source = pd.DataFrame([{"id": 1, "value": None}])
    target = pd.DataFrame([{"id": 1, "value": None}])
    result = reconcile_dataframes(source, target, keys=["id"], compare_columns=["value"])

    assert result.summary["matched_records"] == 1
    assert result.summary["mismatched_records"] == 0


def test_case_insensitive_string_comparison():
    source = pd.DataFrame([{"id": 1, "status": "settled"}])
    target = pd.DataFrame([{"id": 1, "status": "SETTLED"}])
    result = reconcile_dataframes(
        source, target, keys=["id"], compare_columns=["status"], case_sensitive=False
    )

    assert result.summary["matched_records"] == 1


def test_rejects_missing_key_values():
    source = pd.DataFrame([{"id": None, "value": "a"}])
    target = pd.DataFrame([{"id": 1, "value": "a"}])

    with pytest.raises(ValueError, match="Null or blank key"):
        reconcile_dataframes(source, target, keys=["id"], compare_columns=["value"])


def test_supports_composite_keys():
    source = pd.DataFrame(
        [{"account": "A", "date": "2026-01-01", "amount": 10}]
    )
    target = pd.DataFrame(
        [{"account": "A", "date": "2026-01-01", "amount": 10}]
    )
    result = reconcile_dataframes(
        source, target, keys=["account", "date"], compare_columns=["amount"]
    )

    assert result.summary["matched_records"] == 1
