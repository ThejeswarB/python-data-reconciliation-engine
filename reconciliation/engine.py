"""Core reconciliation logic for tabular source and target datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass
class ReconciliationResult:
    """All classification outputs and summary metrics from one run."""

    matched: pd.DataFrame
    mismatched: pd.DataFrame
    mismatch_details: pd.DataFrame
    source_only: pd.DataFrame
    target_only: pd.DataFrame
    source_duplicates: pd.DataFrame
    target_duplicates: pd.DataFrame
    summary: dict[str, object]


def _validate_columns(
    source: pd.DataFrame,
    target: pd.DataFrame,
    keys: list[str],
    compare_columns: list[str],
) -> None:
    if not keys:
        raise ValueError("At least one key column must be supplied.")
    if len(set(keys)) != len(keys):
        raise ValueError("Key columns must not contain duplicates.")
    if len(set(compare_columns)) != len(compare_columns):
        raise ValueError("Comparison columns must not contain duplicates.")
    overlap = set(keys) & set(compare_columns)
    if overlap:
        raise ValueError(
            "Key columns and comparison columns must be separate; "
            f"overlap: {sorted(overlap)}"
        )

    for label, frame in (("source", source), ("target", target)):
        if not frame.columns.is_unique:
            raise ValueError(f"{label} dataset contains duplicate column names.")
        missing = [column for column in keys + compare_columns if column not in frame.columns]
        if missing:
            raise ValueError(f"{label} dataset is missing required columns: {missing}")


def _key_mask(frame: pd.DataFrame, keys: list[str]) -> pd.Series:
    """Return rows whose complete key is non-null and non-empty."""
    mask = frame[keys].notna().all(axis=1)
    for column in keys:
        if pd.api.types.is_string_dtype(frame[column]) or frame[column].dtype == object:
            mask &= frame[column].astype("string").str.strip().ne("").fillna(False)
    return mask


def _merge_keys(left: pd.DataFrame, right: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Build a deterministic key table without relying on pandas index alignment."""
    left_keys = left[keys].drop_duplicates()
    right_keys = right[keys].drop_duplicates()
    return left_keys.merge(right_keys, on=keys, how="outer", indicator=True, validate="one_to_one")


def reconcile_dataframes(
    source: pd.DataFrame,
    target: pd.DataFrame,
    keys: Iterable[str],
    compare_columns: Iterable[str] | None = None,
    *,
    case_sensitive: bool = True,
) -> ReconciliationResult:
    """Reconcile two DataFrames using unique business keys.

    Rows with null/blank keys are rejected. Duplicate-key rows are emitted to
    duplicate reports and excluded from normal classification. Comparison
    treats paired nulls as equal. Values are compared without coercing source
    and target columns into a shared dtype.
    """
    keys = list(keys)
    compare_columns = list(compare_columns) if compare_columns is not None else [
        column for column in source.columns if column not in keys and column in target.columns
    ]
    _validate_columns(source, target, keys, compare_columns)

    source_valid_mask = _key_mask(source, keys)
    target_valid_mask = _key_mask(target, keys)
    if not source_valid_mask.all() or not target_valid_mask.all():
        raise ValueError("Null or blank key values found. Clean or resolve keys before reconciliation.")

    source_dup_mask = source.duplicated(subset=keys, keep=False)
    target_dup_mask = target.duplicated(subset=keys, keep=False)
    source_duplicates = source.loc[source_dup_mask].copy()
    target_duplicates = target.loc[target_dup_mask].copy()

    source_unique = source.loc[~source_dup_mask].copy()
    target_unique = target.loc[~target_dup_mask].copy()

    # Ambiguous keys on either side are kept out of one-to-one classifications.
    ambiguous_source_keys = source_duplicates[keys].drop_duplicates()
    ambiguous_target_keys = target_duplicates[keys].drop_duplicates()
    ambiguous_keys = pd.concat([ambiguous_source_keys, ambiguous_target_keys]).drop_duplicates()

    if not ambiguous_keys.empty:
        source_unique = source_unique.merge(ambiguous_keys.assign(_ambiguous=True), on=keys, how="left")
        source_unique = source_unique[source_unique["_ambiguous"].isna()].drop(columns="_ambiguous")
        target_unique = target_unique.merge(ambiguous_keys.assign(_ambiguous=True), on=keys, how="left")
        target_unique = target_unique[target_unique["_ambiguous"].isna()].drop(columns="_ambiguous")

    merged_keys = _merge_keys(source_unique, target_unique, keys)
    source_only_keys = merged_keys.loc[merged_keys["_merge"] == "left_only", keys]
    target_only_keys = merged_keys.loc[merged_keys["_merge"] == "right_only", keys]
    common_keys = merged_keys.loc[merged_keys["_merge"] == "both", keys]

    source_only = source_unique.merge(source_only_keys, on=keys, how="inner")
    target_only = target_unique.merge(target_only_keys, on=keys, how="inner")

    source_common = source_unique.merge(common_keys, on=keys, how="inner", suffixes=("_source", "_key"))
    target_common = target_unique.merge(common_keys, on=keys, how="inner", suffixes=("_target", "_key"))

    source_common = source_common.set_index(keys).sort_index()
    target_common = target_common.set_index(keys).sort_index()
    target_common = target_common.reindex(source_common.index)

    mismatch_flags = pd.DataFrame(index=source_common.index)
    mismatch_detail_rows: list[dict[str, object]] = []
    column_mismatch_counts: dict[str, int] = {}

    for column in compare_columns:
        left = source_common[column]
        right = target_common[column]
        equal = left.eq(right) | (left.isna() & right.isna())
        if not case_sensitive and (
            pd.api.types.is_string_dtype(left) or left.dtype == object
        ) and (pd.api.types.is_string_dtype(right) or right.dtype == object):
            left_norm = left.astype("string").str.casefold()
            right_norm = right.astype("string").str.casefold()
            equal = left_norm.eq(right_norm) | (left.isna() & right.isna())

        unequal = ~equal.fillna(False)
        mismatch_flags[column] = unequal
        column_mismatch_counts[column] = int(unequal.sum())

        for record_index in source_common.index[unequal]:
            key_values = (record_index,) if len(keys) == 1 else tuple(record_index)
            detail = dict(zip(keys, key_values))
            detail.update(
                {
                    "column": column,
                    "source_value": source_common.at[record_index, column],
                    "target_value": target_common.at[record_index, column],
                }
            )
            mismatch_detail_rows.append(detail)

    any_mismatch = (
        mismatch_flags.any(axis=1)
        if compare_columns
        else pd.Series(False, index=source_common.index)
    )
    matched_index = source_common.index[~any_mismatch]
    mismatched_index = source_common.index[any_mismatch]

    matched = source_common.loc[matched_index].reset_index()
    mismatched_source = source_common.loc[mismatched_index].reset_index()
    mismatched_target = target_common.loc[mismatched_index].reset_index()
    mismatched = mismatched_source.merge(
        mismatched_target,
        on=keys,
        how="inner",
        suffixes=("_source", "_target"),
        validate="one_to_one",
    )
    mismatch_details = pd.DataFrame(
        mismatch_detail_rows,
        columns=keys + ["column", "source_value", "target_value"],
    )

    summary: dict[str, object] = {
        "source_records": len(source),
        "target_records": len(target),
        "matched_records": len(matched),
        "mismatched_records": len(mismatched),
        "source_only_records": len(source_only),
        "target_only_records": len(target_only),
        "source_duplicate_records": len(source_duplicates),
        "target_duplicate_records": len(target_duplicates),
        "comparison_columns": compare_columns,
        "column_mismatch_counts": column_mismatch_counts,
        "mismatch_detail_rows": len(mismatch_details),
    }

    return ReconciliationResult(
        matched=matched,
        mismatched=mismatched,
        mismatch_details=mismatch_details,
        source_only=source_only,
        target_only=target_only,
        source_duplicates=source_duplicates,
        target_duplicates=target_duplicates,
        summary=summary,
    )


def reconcile_csv(
    source_path: str | Path,
    target_path: str | Path,
    keys: Iterable[str],
    compare_columns: Iterable[str] | None = None,
    *,
    case_sensitive: bool = True,
    encoding: str = "utf-8",
) -> ReconciliationResult:
    """Load two CSV files and reconcile them."""
    source = pd.read_csv(source_path, encoding=encoding)
    target = pd.read_csv(target_path, encoding=encoding)
    return reconcile_dataframes(
        source,
        target,
        keys,
        compare_columns,
        case_sensitive=case_sensitive,
    )
