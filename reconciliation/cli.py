"""Command-line interface for the reconciliation engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import reconcile_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile source and target CSV files using business keys."
    )
    parser.add_argument("--source", required=True, help="Path to source CSV file.")
    parser.add_argument("--target", required=True, help="Path to target CSV file.")
    parser.add_argument("--keys", required=True, help="Comma-separated business key columns.")
    parser.add_argument("--compare", default=None, help="Comma-separated columns to compare.")
    parser.add_argument("--output", default="output", help="Directory for generated reports.")
    parser.add_argument("--case-insensitive", action="store_true", help="Ignore case in string comparisons.")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default: utf-8).")
    return parser


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

    result = reconcile_csv(
        args.source,
        args.target,
        keys,
        compare_columns,
        case_sensitive=not args.case_insensitive,
        encoding=args.encoding,
    )

    reports = {
        "matched": result.matched,
        "mismatched": result.mismatched,
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
    print(json.dumps(result.summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
