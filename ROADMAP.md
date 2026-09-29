# Roadmap

Current focus: correctness and reproducibility of the existing small suite, not the number of bundled algorithms.

The v0.1.1 maintenance work addresses concrete false-stopping/evidence counterexamples, strengthens release integrity and adds a runnable trajectory example. These are maintainer/assistant-assisted checks, not independent external review.

Next meaningful improvements are independently reported reproduction results, an external review of the source-to-formula mappings, and representative new fixtures that expose a documented gap. A new method should arrive with a public source and an independently checkable experiment rather than simply increasing feature count.

Known scope limits remain: dense small fixtures, finite float64 arithmetic, no sparse/complex solver API, no production-solver guarantee, and no universal theorem certification.
