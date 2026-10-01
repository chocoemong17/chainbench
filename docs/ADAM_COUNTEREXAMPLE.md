# Adam: memory, projection and online regret

```bash
python -m chainbench reproduce reddi-2018 --lang ko --output adam.html
python -m chainbench reproduce reddi-2018 --steps 4 --format json --output four.json
```

Open the HTML offline. Choose one of nine cases and inspect every actual round
for both methods. The number line shows the pre-update point, unconstrained
proposal and projected point. Bars compare the exponential second moment with
the memory actually used in the denominator. All paths, native selected-round
tables and complete JSON are included. No script computes a new optimizer path.
The default budget is 3,000; integer budgets 1 through 12,000 are accepted.

The development `tour --extended` also includes this default report as
`adam.html`. Its guide links the two published counterexamples while keeping
fixed-objective gap and changing-loss regret distinct. The preview uses the
actual C=3, alpha-fraction-0.1 regret chart, retaining the slow AMSGrad case.
Both reports link back to each other; the numerical records are unchanged.
[Bundle settings and source-bound navigation](OFFLINE_TOUR.md).

## Exact source and the instantiated family

Reddi, Kale and Kumar, *On the Convergence of Adam and Beyond*, ICLR 2018.
Use [arXiv:1904.09237v1](https://arxiv.org/pdf/1904.09237v1), uploaded 2019-04-19:

| Source location | Implemented scope |
| --- | --- |
| Algorithm 1 / Eq. (1), p.3; footnote 1 | Analysis variant without moment debiasing |
| Section 3 / Theorem 1, p.4 | Period-three online linear losses on [−1,1] |
| Appendix A / Eqs. (4)–(6), pp.10–11 | x₁=1, αₜ=α/√t and 0<α<√(1−β₂) |
| Algorithm 2, p.5 | AMSGrad maximum of successive second moments |
| Eq. (2), p.4 | Change in inverse effective learning rate |

The source defines a family, rather than the exact finite inputs used here.
We declare the full Cartesian product C∈{3,10,100} and
α/√(1−β₂)∈{0.1,0.5,0.9}. Set β₂=1/(1+C²), β₁=0, ε=0 and initial
first moment, second moment and maximum memory to zero. There is no seed.
Keep both methods and all nine settings regardless of outcomes.

This is **Theorem 1 / Appendix A**, not Figure 1. Section 5's Figure 1 uses a
different period-101 sequence, gradients 1010 and −10, and β₁=0.9, β₂=0.99.
The implementation also does not add debiasing, epsilon or unconstrained
neural-network training from a modern optimizer library.

The public PDF's final block-sum display on p.11 repeats one round subscript.
We sum each of the three actual losses once. The bound below follows directly
from those three distinct terms and the stated iterate inequalities; the
printed duplicated subscript is not transcribed as a recurrence.
Paper PDFs and third-party code are not bundled.

## One actual round

For t=1,…,T, set gₜ=C when t≡1 modulo 3 and gₜ=−1 otherwise.
Incur fₜ(xₜ)=gₜxₜ **before** updating. Then

```text
m_t = g_t                         (beta1 = 0)
v_t = beta2*v_(t-1) + (1-beta2)*g_t^2
memory_t = v_t                    (Adam)
memory_t = max(memory_(t-1), v_t)  (AMSGrad)
eta_t = (alpha/sqrt(t)) / sqrt(memory_t)
proposal_t = x_t - eta_t*g_t
x_(t+1) = clip(proposal_t, -1, 1)
```

In one dimension the positive weighted projection in the source is exactly
this interval clip. The chosen gradients are nonzero, so every denominator
is positive without epsilon. Losses, proposals, clipping corrections and
displacements are the actual floating-point values, including roundoff.
No method stops early or appends a synthetic loss at x_(T+1).

The number line always spans [−2,2]. This contains the actual proposals:
vₜ≥(1−β₂)gₜ² and AMSGrad's memory is at least vₜ, so
|ηₜgₜ|≤α/√(t(1−β₂))<1. Bars have a fixed [0,C²] scale in each case.
The second moment is not a centered statistical variance.

### Reading one three-round block

The block inspector groups the stored rounds `3j+1, 3j+2, 3j+3`. It shares the
case/round selector with the single-round inspector, highlights the selected
round and also shows later rounds already computed within the same block.
Every block and both methods use the fixed position axis [−2,2]. Blue markers
are pre-update positions, hollow amber markers are proposals, green markers
are projected positions. Dark segments show actual displacement and amber
segments show clipping. Vertical rows indicate update order, not another
coordinate or a loss axis.

The accompanying ledger keeps the signs of `g`, the effective rate, actual
post-projection `displacement`, `after−proposal` and `g*(before+1)`. A positive
sum of gradients does not determine the sum of differently normalized,
projected moves. For example, C=3 and alpha fraction 0.5 starts with a move of
−0.5, then two positive moves return Adam to 1; the second and third regret
contributions are negative. AMSGrad keeps the larger denominator memory and
does not return to 1 in this first block. These are readings of the existing
paths, not extra optimizer runs or an extension of the theorem's scope.

The complete block's regret is copied from its stored three-term `fsum`;
`source_lower=2C−4` is present only for complete Adam blocks. If the budget ends
after one or two phases, the inspector shows exactly those phases and labels
complete-block regret and its lower reference not applicable. It does not
invent future updates, a partial-cycle bound, or an AMSGrad lower bound.
Every case also has a native first-block diagram and ledger without JavaScript;
all later blocks are available in the interactive inspector and full JSON.

The browser audit checks every block on desktop, all selected native rounds
on mobile, and each native first block without page scripts. It independently
aggregates the per-round regret contributions and checks all displayed signed
values, marker/segment coordinates, phase coverage and selected-row highlights.
The underlying JSON, recurrence, path charts and source references are unchanged.

We record Γₜ=√memoryₜ/αₜ−√memoryₜ₋₁/αₜ₋₁ for t≥2, the current-minus-previous
form of Eq. (2). Γ₁ is null: there is no invented α₀. Negative Γ indicates
an increasing effective learning rate. AMSGrad's max-memory and decreasing
αₜ make this quantity nonnegative for these inputs.

## What the regret reference means

Each prefix gradient sum G_T is positive because C>2. The best fixed
comparator is therefore x=−1, with cumulative loss −G_T:

```text
R_T = sum(g_t*x_t) - min_{x in [-1,1]} sum(g_t*x)
    = sum(g_t*(x_t+1)).
```

An individual increment can be negative. Average regret at T=0 is undefined.
This is not an objective gap for a single fixed function, and the terminal
iterate is not itself a regret value. The record retains the raw difference
between accumulated increments and cumulative loss plus G_T; finite sums
need not give exactly identical floats.

The source argument gives x_(3j+1)=1 and positive iterates. A complete block
has regret at least 2C−4, hence R_(3j)/(3j)≥2(C−2)/3. Orange chart dots
appear only at completed three-round blocks and only describe the Adam
variant. They are not bounds for AMSGrad or an extension to partial cycles.

All computed Adam paths remain positive and return to 1 after each complete
block in the supported inputs/budgets. At the default budget, the AMSGrad
case C=3, alpha fraction 0.1 still ends near −0.248184, with average regret
above 0.38. This deliberately retained slow case prevents a claim that all
finite AMSGrad paths have already reached −1. The other finite observations
do not establish asymptotic convergence or a universal performance ranking.

## Record and independent validation

`x[j]` means x_(j+1), length T+1. Every other method series has length T;
element j belongs to round j+1. Source metadata, all settings, full schedules,
complete cycles, observations and environment accompany the arrays. Each case
fingerprints sorted-key compact JSON inputs with SHA-256. Initial moments and
the absence of debiasing/epsilon are explicit, rather than implicit defaults.

`scripts/smoke_adam_counterexample.py` imports neither ChainBench nor NumPy.
It rebuilds the recurrence with 60-digit Decimal arithmetic, independent square
roots, closed-form prefix gradient sums and an independent comparator. It
checks every round, both methods, all nine cases, source scope, input hashes,
actual loss timing and raw roundoff fields. Ordinary values use rtol=3e−12,
atol=2e−13; moments/rates use no absolute floor; accumulated sums allow
atol=2e−10. Exact structural and actual-float identities are checked separately.
Budgets 1,4,3000,12000 include initial, partial-cycle, default and maximum cases.

Tests include a hand-computed first block, the slow AMSGrad case, overwrite
protection, full chart-coordinate coverage and corruptions of bias correction,
epsilon, timing, memory, scope, hashes and observations. The browser checker
operates the real selectors and verifies displayed values, proposal/clip
coordinates and memory bars against the independently audited record. Its
wide viewport traverses every round; the narrow viewport checks all native
rounds and keyboard navigation. No-JavaScript tables and JSON downloads are
also checked, with external network requests rejected.

The installed-workflow harness requires this reproduction for both wheel and
sdist evidence; the release gate requires a matching `adam_counterexample`
entry. Local execution from built archives is distinct from an isolated install
and from remote GitHub Actions. The fixed literature check suite and the
guided-tour reports keep their previous calculations.
