"""Command-line interface for the reconciliation engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import reconcile_files
from .reports import write_excel_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile source and target CSV or Excel files using business keys."
    )
    parser.add_argument("--source", required=True, help="Path to source CSV/XLSX/XLSM file.")
    parser.add_argument("--target", required=True, help="Path to target CSV/XLSX/XLSM file.")
    parser.add_argument("--keys", required=True, help="Comma-separated business key columns.")
    parser.add_argument("--compare", default=None, help="Comma-separated columns to compare.")
    parser.add_argument("--output", default="output", help="Directory for generated reports.")
    parser.add_argument("--source-sheet", default=0, help="Source Excel sheet name or zero-based index.")
    parser.add_argument("--target-sheet", default=0, help="Target Excel sheet name or zero-based index.")
    parser.add_argument("--case-insensitive", action="store_true", help="Ignore case in string comparisons.")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default: utf-8).")
    parser.add_argument(
        "--no-excel-report",
        action="store_true",
        help="Skip the formatted Excel workbook and generate CSV/JSON reports only.",
    )
    return parser


def _sheet_value(value: int | str) -> int | str:
    """Convert numeric sheet arguments to zero-based indices."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except ValueError:
        return value


def main() -> int:
    args = build_parser().parse_args()
    keys = [item.strip() for item in args.keys.split(",") if item.strip()]
    compare_columns = (
        [item.strip() for item in args.compare.split(",") if item.strip()]
        if args.compare
        else None
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = reconcile_files(
        args.source,
        args.target,
        keys,
        compare_columns,
        source_sheet=_sheet_value(args.source_sheet),
        target_sheet=_sheet_value(args.target_sheet),
        case_sensitive=not args.case_insensitive,
        encoding=args.encoding,
    )

    reports = {
        "matched": result.matched,
        "mismatched": result.mismatched,
        "mismatch_details": result.mismatch_details,
        "source_only": result.source_only,
        "target_only": result.target_only,
        "source_duplicates": result.source_duplicates,
        "target_duplicates": result.target_duplicates,
    }
    for name, frame in reports.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)

    (output_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2), encoding="utf-8"
    )

    if not args.no_excel_report:
        excel_path = output_dir / "reconciliation_report.xlsx"
        write_excel_report(result, excel_path)
        print(f"Excel report: {excel_path}")

    print(json.dumps(result.summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
