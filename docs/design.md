# Design Notes

## First release scope

The first release is a local CSV reconciliation engine. It provides a testable processing core and CLI. A UI and distributed backend are deliberately deferred until correctness and expected client requirements are established.

## Classification model

- Matched: a unique business key exists once in each dataset and selected comparison columns are equal.
- Mismatched: a unique business key exists once in each dataset but at least one selected comparison column differs.
- Source-only: a unique, non-ambiguous key exists only in source.
- Target-only: a unique, non-ambiguous key exists only in target.
- Duplicate: a key occurs more than once in a dataset. Duplicate-key rows are reported separately and not automatically paired.

If a key is duplicated on either side, that key is considered ambiguous and excluded from all four normal classifications. This conservative behavior avoids producing misleading matches.

## Comparison behavior

- Null values compare equal to other null values.
- By default string comparisons are case-sensitive.
- Optional case-insensitive comparison uses Unicode case folding.
- Keys must be non-null and non-blank.
- Comparison fields are explicit when passed to the API/CLI; otherwise common non-key columns from the source are used.

## Performance and future work

The initial implementation loads files into pandas DataFrames and is suitable for datasets that fit comfortably in available memory. Before claiming large-file capacity, benchmark with generated datasets and document hardware and results. A future Spark implementation should reuse the classification contract and be tested against the pandas implementation on the same fixtures.
