from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckStory:
    source: str
    claim: str
    evidence: str
    takeaway: str
    caveat: str


STORIES = {
    "gd-baseline": CheckStory(
        source="Gradient descent baseline (smooth convex)",
        claim="With step 1/L, gradient descent has an O(1/k) objective-gap guarantee.",
        evidence=(
            "ChainBench plots the measured objective gap on one exact-reference smooth convex "
            "quadratic together with the standard L*R^2/(2k) envelope."
        ),
        takeaway="The observed gap should remain below the displayed O(1/k) envelope.",
        caveat="One deterministic fixture is evidence about this implementation, not a proof.",
    ),
    "nesterov-1983": CheckStory(
        source="Nesterov-style acceleration / fixed-L smooth FISTA",
        claim=(
            "Acceleration changes the familiar smooth-convex objective-gap rate from O(1/k) "
            "to O(1/k^2) for the implemented fixed-L recurrence."
        ),
        evidence=(
            "The plot overlays the accelerated trajectory with the 2*L*R^2/(k+1)^2 envelope."
        ),
        takeaway="The important visual is the faster curved decay and its O(1/k^2) envelope.",
        caveat=(
            "The historical CLI slug is retained, but the code follows the fixed-L FISTA-style "
            "recurrence documented in Beck--Teboulle (2009), not a literal 1983 transcription."
        ),
    ),
    "polyak-1964": CheckStory(
        source="Polyak heavy-ball on a strongly convex quadratic",
        claim="Classically tuned heavy-ball has a quadratic spectral contraction prediction rho.",
        evidence="ChainBench plots consecutive Euclidean error ratios and the predicted rho line.",
        takeaway="In the tail, the observed ratios should approach the spectral prediction.",
        caveat=(
            "The 8% comparison threshold is an explicit empirical regression tolerance, not a "
            "constant from Polyak's theorem."
        ),
    ),
    "hestenes-stiefel-1952": CheckStory(
        source="Conjugate gradient for SPD systems",
        claim=(
            "CG's energy-norm error is controlled by a condition-number envelope involving "
            "((sqrt(kappa)-1)/(sqrt(kappa)+1))^k."
        ),
        evidence="The plot shows the observed Q-norm error against the classical upper envelope.",
        takeaway="The observed energy error should stay under the displayed condition-number bound.",
        caveat=(
            "Finite precision can change stopping behavior; this is not a claim of exact n-step "
            "termination or a universal residual-to-forward-error guarantee."
        ),
    ),
    "jaggi-2013": CheckStory(
        source="Frank-Wolfe / conditional gradient",
        claim="With bounded curvature and the standard step schedule, primal gap decays as O(1/k).",
        evidence=(
            "The simplex experiment overlays the measured primal gap with the curvature-based "
            "2*C_f/(k+2) envelope."
        ),
        takeaway="The measured gap should remain below the curvature-based O(1/k) curve.",
        caveat="The fixture uses an exact linear minimization oracle on one synthetic simplex problem.",
    ),
    "rockafellar-1976": CheckStory(
        source="Exact proximal point on a strongly convex quadratic",
        claim=(
            "For this exact quadratic specialization, each proximal step contracts Euclidean "
            "error by at most q=1/(1+c*mu)."
        ),
        evidence=(
            "The plot compares the measured distance to the optimizer with q^k times the initial "
            "distance."
        ),
        takeaway="The error trajectory should contract no slower than the displayed geometric envelope.",
        caveat=(
            "This is an exact quadratic resolvent calculation, not Rockafellar's full inexact "
            "monotone-operator theory."
        ),
    ),
    "beck-teboulle-2009": CheckStory(
        source="Beck--Teboulle FISTA on composite convex optimization",
        claim="Fixed-L FISTA has an O(1/k^2) composite objective-gap guarantee.",
        evidence=(
            "On an exact-solvable diagonal LASSO fixture, the measured composite gap is plotted "
            "against the 2*L*R^2/(k+1)^2 envelope."
        ),
        takeaway="The important visual is the O(1/k^2) envelope together with the measured FISTA gap.",
        caveat=(
            "This is a transparent diagonal LASSO example, not a reproduction of the paper's "
            "image-deblurring experiments."
        ),
    ),
    "ista-vs-fista": CheckStory(
        source="ISTA and FISTA on the same diagonal LASSO fixture",
        claim=(
            "This trajectory comparison illustrates the practical effect of acceleration on one "
            "controlled problem."
        ),
        evidence="The plot places ISTA and FISTA objective gaps on the same iteration axis.",
        takeaway="On this fixture FISTA's gap falls faster, making the acceleration effect easy to see.",
        caveat=(
            "This row is INFO only: the experiment is not a theorem that FISTA beats ISTA at every "
            "iteration, on every problem, or at equal computational cost."
        ),
    ),
}
