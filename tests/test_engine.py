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
    assert result.mismatch_details.to_dict("records") == [
        {"id": 102, "column": "amount", "source_value": 700, "target_value": 750}
    ]
    assert result.summary["column_mismatch_counts"] == {"name": 0, "amount": 1}


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
    assert result.mismatch_details.empty


def test_case_insensitive_string_comparison():
    source = pd.DataFrame([{"id": 1, "status": "settled"}])
    target = pd.DataFrame([{"id": 1, "status": "SETTLED"}])
    result = reconcile_dataframes(
        source, target, keys=["id"], compare_columns=["status"], case_sensitive=False
    )

    assert result.summary["matched_records"] == 1
    assert result.mismatch_details.empty


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


def test_reports_each_mismatched_field_for_a_record():
    source = pd.DataFrame([{"id": 1, "status": "PENDING", "amount": 100}])
    target = pd.DataFrame([{"id": 1, "status": "PROCESSED", "amount": 120}])

    result = reconcile_dataframes(
        source, target, keys=["id"], compare_columns=["status", "amount"]
    )

    assert result.summary["mismatched_records"] == 1
    assert result.summary["mismatch_detail_rows"] == 2
    assert set(result.mismatch_details["column"]) == {"status", "amount"}
    assert set(result.mismatch_details["source_value"]) == {"PENDING", 100}
    assert set(result.mismatch_details["target_value"]) == {"PROCESSED", 120}



def test_reconcile_files_reads_excel_workbooks(tmp_path):
    from reconciliation.engine import reconcile_files

    source = pd.DataFrame(
        [{"id": 1, "amount": 100}, {"id": 2, "amount": 200}]
    )
    target = pd.DataFrame(
        [{"id": 1, "amount": 100}, {"id": 2, "amount": 250}]
    )
    source_path = tmp_path / "source.xlsx"
    target_path = tmp_path / "target.xlsx"
    source.to_excel(source_path, sheet_name="Transactions", index=False)
    target.to_excel(target_path, sheet_name="Transactions", index=False)

    result = reconcile_files(
        source_path,
        target_path,
        keys=["id"],
        compare_columns=["amount"],
        source_sheet="Transactions",
        target_sheet="Transactions",
    )

    assert result.summary["matched_records"] == 1
    assert result.summary["mismatched_records"] == 1
    assert result.mismatch_details.iloc[0]["column"] == "amount"


def test_excel_report_contains_formatted_sheets(tmp_path):
    from openpyxl import load_workbook
    from reconciliation.engine import reconcile_dataframes
    from reconciliation.reports import write_excel_report

    source = pd.DataFrame([{"id": 1, "status": "PENDING", "amount": 100}])
    target = pd.DataFrame([{"id": 1, "status": "PROCESSED", "amount": 120}])
    result = reconcile_dataframes(
        source, target, keys=["id"], compare_columns=["status", "amount"]
    )

    output_path = tmp_path / "reports" / "reconciliation_report.xlsx"
    write_excel_report(result, output_path)

    workbook = load_workbook(output_path, data_only=True)
    assert workbook.sheetnames == [
        "Summary", "Matched", "Mismatched", "Mismatch Details",
        "Source Only", "Target Only", "Source Duplicates", "Target Duplicates"
    ]
    assert workbook["Summary"]["A1"].value == "Reconciliation Report"
    assert workbook["Summary"]["A4"].value == "Metric"
    assert workbook["Summary"]["B4"].value == "Value"
    assert workbook["Summary"]["A16"].value == "Column-level Mismatch Counts"
    assert workbook["Summary"]["A17"].value == "Comparison Column"
    assert workbook["Summary"]["B17"].value == "Mismatched Records"
    assert workbook["Summary"]["A18"].value == "status"
    assert workbook["Summary"]["B18"].value == 1
    assert workbook["Summary"]["A19"].value == "amount"
    assert workbook["Summary"]["B19"].value == 1
    assert workbook["Mismatch Details"].max_row == 3
    assert workbook["Mismatch Details"].freeze_panes == "A2"
    assert workbook["Mismatch Details"].auto_filter.ref is not None
    workbook.close()


def test_read_table_rejects_unsupported_extensions(tmp_path):
    from reconciliation.engine import read_table

    unsupported = tmp_path / "data.txt"
    unsupported.write_text("id,value\\n1,a\\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Supported formats"):
        read_table(unsupported)
