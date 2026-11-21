# Python Data Reconciliation Engine

A configurable Python tool for reconciling CSV and Excel datasets and producing clear, auditable discrepancy reports.

> Portfolio project by Basu. This repository uses synthetic sample data and original implementation code.

## Features

- Compare two CSV or Excel workbooks using one or more business keys.
- Select worksheet names or zero-based worksheet indices for Excel inputs.
- Classify matched, mismatched, source-only, and target-only records.
- Detect duplicate keys instead of silently choosing one record.
- Apply an optional absolute numeric tolerance for rounding or precision differences.
- Produce record-level and field-level mismatch reports.
- Export a formatted Excel workbook with eight sheets.
- Generate CSV reports and a machine-readable JSON summary.

## Quick start

Requires Python 3.10 or later.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

### Reconcile two CSV files

```bash
python -m reconciliation.cli \
  --source data/sample/source.csv \
  --target data/sample/target.csv \
  --keys transaction_id \
  --compare amount,status,customer \
  --output output
```

### Reconcile Excel workbooks

```bash
python -m reconciliation.cli \
  --source data/client_source.xlsx \
  --target data/client_target.xlsx \
  --source-sheet Transactions \
  --target-sheet Transactions \
  --keys transaction_id \
  --compare amount,status \
  --numeric-tolerance 0.01 \
  --output output
```

`--numeric-tolerance 0.01` treats numeric values as equal when their absolute difference is at most 0.01. The default is 0, which requires exact numeric equality. The tolerance applies only when both sides of a comparison column are numeric.

CSV and Excel files can also be mixed in the same run. For example, the source can be a CSV while the target is an XLSX workbook.

## Generated reports

The output directory contains:

- `reconciliation_report.xlsx` — formatted workbook with Summary, Matched, Mismatched, Mismatch Details, Source Only, Target Only, Source Duplicates, and Target Duplicates sheets.
- `summary.json` — machine-readable metrics and per-column mismatch counts.
- Individual CSV files for each classification, including field-level mismatch details.

To skip Excel report generation, pass `--no-excel-report`.

## Matching rules

1. Key columns identify a business record. Use a composite key by passing multiple column names separated by commas.
2. Comparison columns are checked separately from keys.
3. A key present once in each input is compared across the selected comparison columns.
4. A key present in only one input is classified as source-only or target-only.
5. Keys duplicated within either input are reported separately and excluded from one-to-one classification.
6. Empty key values are rejected by default.
7. Paired null comparison values are treated as equal. String comparisons are case-sensitive by default.
8. Numeric tolerance is an absolute threshold applied only to columns whose source and target values are both numeric.

## Supported formats and limitations

- CSV: read using pandas.
- Excel: `.xlsx` and `.xlsm`, read using openpyxl.
- Older binary `.xls` files are not supported by this version.
- Entire datasets are loaded into memory; this release is intended for files that fit comfortably in available memory.
- No web UI, database persistence, or Spark backend yet.

## Tests

```bash
python -m pytest -q
```

GitHub Actions runs the test suite on Python 3.10, 3.11, and 3.12.

## Responsible use

Use only data you are authorized to process. Do not commit customer data, credentials, production extracts, or confidential employer material to this repository.
