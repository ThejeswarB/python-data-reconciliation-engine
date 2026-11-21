# Design Notes

## First release scope

The first release supports local CSV and Excel reconciliation. It provides a testable processing core, command-line interface, CSV artifacts, and a formatted Excel report. A UI and distributed backend are deliberately deferred until correctness and expected client requirements are established.

## Input handling

- CSV inputs are read using pandas.
- Excel `.xlsx` and `.xlsm` inputs are read using openpyxl through pandas.
- Excel worksheet selection accepts a sheet name or zero-based index.
- The source and target input formats may differ.
- Older `.xls` files are not supported.

## Classification model

- Matched: a unique business key exists once in each dataset and selected comparison columns are equal.
- Mismatched: a unique business key exists once in each dataset but at least one selected comparison column differs.
- Source-only: a unique, non-ambiguous key exists only in source.
- Target-only: a unique, non-ambiguous key exists only in target.
- Duplicate: a key occurs more than once in a dataset. Duplicate-key rows are reported separately and not automatically paired.

If a key is duplicated on either side, that key is considered ambiguous and excluded from all four normal classifications. This conservative behavior avoids producing misleading matches.

## Mismatch reporting

The record-level mismatch report keeps source and target columns side by side. The field-level mismatch report emits one row per differing comparison field, including the business key, column name, source value, and target value. The JSON summary records mismatch counts per comparison column.

## Excel output

The formatted workbook contains Summary, Matched, Mismatched, Mismatch Details, Source Only, Target Only, Source Duplicates, and Target Duplicates sheets. It applies styled headers, frozen header rows, filters, adjusted column widths, and distinct fills for source and target values in the field-level mismatch sheet.

## Comparison behavior

- Null values compare equal to other null values.
- By default string comparisons are case-sensitive.
- Optional case-insensitive comparison uses Unicode case folding.
- Keys must be non-null and non-blank.
- Comparison fields are explicit when passed to the API/CLI; otherwise common non-key columns from the source are used.

## Performance and future work

The implementation loads files into pandas DataFrames and is suitable for datasets that fit comfortably in available memory. Before claiming large-file capacity, benchmark with generated datasets and document hardware and results. A future Spark implementation should reuse the classification contract and be tested against the pandas implementation on the same fixtures.
