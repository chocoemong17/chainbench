# Contributor and agent notes

Scope: independently implement public, published algorithms and explain their numerical behavior. Do not add private research, unpublished derivations, personal identities, private datasets, paper PDFs or third-party source code without an appropriate license.

Read docs/SOURCE_MAP.md before changing mathematical claims. Distinguish historical algorithm attribution, the actual implemented recurrence and the exact finite check. INFO observations are not theorem tests. Never turn missing/non-finite evidence into a successful result.

Run ruff check ., python -m pytest, chainbench check all, python -m build and python scripts/smoke_install.py as appropriate. A built wheel is not evidence that it installs correctly. Snapshot numeric comparisons have documented tolerances.

Use substantive PRs and one coherent commit per tested change where possible; do not generate artificial contributor activity. Preserve real review and CI outcomes, including failures. Do not fabricate users, stars, downloads or endorsements.

Publishing is restricted to the tested main-branch commit through the gated release workflow. Do not overwrite releases, enable paid services, publish to registries, alter account security, or disable protective checks to force a release.
