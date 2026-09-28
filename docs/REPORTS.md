# Reports

ChainBench can serialize the complete check suite without adding plotting or
data-frame dependencies.

## Terminal

Run all checks in the human-readable terminal format:

    chainbench check all

## Markdown

    chainbench report --format markdown

Write a report to disk:

    chainbench report --format markdown --output report.md

## CSV

    chainbench report --format csv --output report.csv

CSV is useful for spreadsheets or downstream scripts.

## JSON

    chainbench report --format json --output report.json

The report command returns a non-zero exit status if any registered numerical
condition is inconsistent. This makes the same command useful in local
reproduction work and CI.

The checked-in benchmark snapshot at `benchmarks/latest.md` is intentionally
deterministic and contains no timestamps. It can therefore be reviewed as a
normal source diff when algorithmic behavior changes.
