# ChainBench v0.1.1 — numerical and release-evidence fixes

This experimental alpha maintenance release fixes counterexamples found after v0.1.0. The original published v0.1.0 artifacts remain unchanged.

## Correctness

- CG no longer mistakes an underflowed or overflowed residual norm for convergence. It solves a normalized correction equation and checks the true residual before stopping. Global matrix/RHS scales of 1e-200 and 1e200 are covered by regression tests.
- CG traces report `termination` (`converged` or `max_steps`) and the actual residual norm. The relative-to-initial-residual tolerance convention is preserved.
- Quadratic reference solutions and symmetry are checked relative to scale; a tiny nonzero stationarity residual is no longer hidden by an absolute acceptance floor. Symmetrization avoids `Q+Q.T` overflow.
- Missing, boolean/string or nonfinite observations, malformed bound samples, mismatched INFO thresholds and empty suites cannot silently become successful evidence.

## Validation and usability

Small hand-computed recurrence tests distinguish GD, CG, heavy-ball, FISTA and proximal point. A targeted fault-injection script confirms that four deliberate errors are caught by assertion failures; this is not a claim of exhaustive mutation coverage or independent review.

A new `examples/compare_quadratic.py` exports inspectable trajectories on a deterministic rotated quadratic. `docs/QUICKSTART.md` explains installation, CG termination, output interpretation and limitations.

## Publication integrity

The publishing gate rechecks each artifact's installation-record hash, source commit, statuses and checksums immediately before upload. Unexpected files, duplicate records, missing evidence and wrong-target existing tags are rejected. Uploaded assets are downloaded and compared before publication. Network errors do not masquerade as absent tags or releases, and existing releases are never overwritten.

The release remains a small NumPy-only teaching/reproducibility tool. No private research, real-name maintainer metadata, API calls, paid services or PyPI publishing have been added. See the attached verification report and checksums for the actual installed distributions.
