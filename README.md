# Python Data Reconciliation Engine

A configurable Python tool for reconciling two tabular datasets and producing clear, auditable discrepancy reports.

> Portfolio project by Basu. This repository uses synthetic sample data and original implementation code.

## Goals

- Compare source and target CSV datasets using one or more business keys.
- Classify matched, mismatched, source-only, and target-only records.
- Detect duplicate keys instead of silently choosing one record.
- Generate a machine-readable reconciliation summary and detailed CSV reports.
- Provide clear validation errors for missing keys, duplicate column names, and invalid input.

## Current implementation

The first version provides a local CSV reconciliation engine built with Python's standard library and pandas. It is intentionally designed as a reliable, testable core before adding a web interface or distributed Spark processing.

## Quick start

Requires Python 3.10 or later.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m reconciliation.cli \
  --source data/sample/source.csv \
  --target data/sample/target.csv \
  --keys transaction_id \
  --compare amount,status \
  --output output
```

On Windows PowerShell, run the CLI command on one line or use PowerShell's backtick for line continuation.

The command writes:
- `summary.json`
- `matched.csv`
- `mismatched.csv`
- `source_only.csv`
- `target_only.csv`
- `source_duplicates.csv`
- `target_duplicates.csv`

## Matching rules

1. Key columns identify a business record. Use a composite key by passing multiple column names separated by commas.
2. Comparison columns are checked separately from keys.
3. A key present once in each input is matched, then compared across the selected comparison columns.
4. A key present in only one input is classified as source-only or target-only.
5. Keys duplicated within either input are reported separately and excluded from one-to-one classification. This avoids ambiguous matching and inflated results.
6. Empty key values are rejected by default because they do not reliably identify a record.

## Project structure

```text
reconciliation/
  __init__.py
  engine.py
  cli.py
tests/
  test_engine.py
data/sample/
  source.csv
  target.csv
docs/
  design.md
output/                 # generated reports; ignored by git
```

## Development and tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitations in this version

- CSV inputs only.
- Entire datasets are loaded into memory.
- Duplicate-key records are reported, not automatically paired.
- No web UI, database persistence, or Spark backend yet.

These are deliberate scope boundaries for the initial release. Planned enhancements are tracked in the project documentation.

## Responsible use

Use only data you are authorized to process. Do not commit customer data, credentials, production extracts, or confidential employer material to this repository.
