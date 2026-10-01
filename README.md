# Preserved development reviews and source history

This archive contains 41 generated review PDFs and the complete local Git refs captured on 2026-10-01. These are historical review documents, not claims that current remote CI has passed. The SHA-256 and Git blob identifiers for every file are in manifest.json.

Current work: [PR #73](https://github.com/chocoemong17/chainbench/pull/73). The source and cloud report generator are on `work/cloud-learning-toolkit`.

`source/all-local-refs.bundle` preserves the original development commit history and branch names. Inspect it with `git bundle list-heads`, or clone it into a new directory with `git clone source/all-local-refs.bundle recovered`. `source/pre-migration-source.tar.gz` preserves all source files, including the latest uncommitted FISTA tour edits, just before cloud-workflow changes.

Large generated HTML copies and temporary test outputs were disposable. The cloud reading bundle workflow regenerates the complete current 25-page tour on GitHub Actions. Raw local logs, credentials, third-party paper PDFs and installed dependencies are not in this archive.
