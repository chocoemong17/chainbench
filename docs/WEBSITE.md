# Browser-first learning

The website is built for students and developers encountering optimization papers
for the first time. Its first route is **watch → drag → read the equation → open
the paper report**. English is the default; the language switch selects Korean
and remembers the choice across report navigation when browser storage is available.
An explicit `?lang=en` or `?lang=ko` takes precedence.

The first explorer computes gradient descent and the smooth specialization of
fixed-L FISTA in the browser. Three constructed SPD quadratics use condition
numbers 3, 20 and 80 and rotations 0°, 32° and −35°. Their known optimum is
(1, −0.8), their start is (−1.55, 1.45), and their budget is 60 updates. The
numerical reference comes from `chainbench.landscape.run_landscape`; browser
checks compare every iterate and gap against it, for each input and method.
There is no claim that these are original-paper data, a universal algorithm
ranking, or an equal-time comparison. The inspector computes actual updates;
it does not interpolate optimizer states to make a smoother-looking result.

The 30-second explanation advances one actual iteration every half second.
It starts only on request, can be paused or scrubbed, and stops on tab hiding.
Changing cases and Reset stop playback. Keyboard navigation works on the native
range control. Reduced-motion readers receive no automatic animation.

The separate image-recovery report scrubs **recorded snapshots**, whose iteration
spacing is nonuniform. Its timeline labels show actual k values. Images and
metrics always select the same existing numerical row; intervening image states
are not invented. The exact selector and non-script gallery remain available.

Core atlas bounds and the introductory gradient equation use native MathML for
fractions, roots and indices without a remote script service. Other authored
formula blocks replace sparse Unicode scripts with native sub/sup elements and
retain their original mathematical case and horizontally scrollable lines.
Numerical JSON and SVG labels are not transformed. Readable formulas and the
report gallery remain available when scripts are disabled.

## Build and publication

The `tests` workflow first generates and audits the complete bilingual reading
tour. `scripts/build_site.py` verifies those exact source digests, then copies
the 25 HTML reports with English initial language and return navigation. It
records the source tour and transformed file hashes in `site-manifest.json`.
Historical release ZIPs/PDFs retain their original bytes and language.

Chromium and WebKit check desktop/mobile navigation, numeric equivalence, real
pointer dragging, keyboard stepping, play/pause, language persistence, native
fraction layout, all report URLs, missing-data and no-script paths, external
requests, JavaScript errors and horizontal overflow. Screenshots and proof JSON
are stored as Actions artifacts, with seven-day retention.

`publish verified website` runs only after the complete `tests` workflow passes
on a push to current `main`. It verifies the source and file inventory of that
run's website artifact before GitHub Pages publication. It never deploys PR
artifacts or regenerates untested HTML during deployment. A failure leaves the
last successful website intact.

The repository's **Settings → Pages → Build and deployment → Source** must be
**GitHub Actions** once, using an account with repository administration access.
The expected URL is `https://chocoemong17.github.io/chainbench/`; consider it live
only after the deployment succeeds and the public URL is checked.

## Six visual paper lessons

The paper collection includes Adam, Attention, ResNet, Backpropagation, CNN and
Dropout. The new foundations films run 59s, 44.72s and 30s. Each has two draggable
diagrams and English/Korean media. [Exact sources and verification](FOUNDATIONS.md).
The complete website gate also runs the foundations browser audit on Chromium
and WebKit, desktop and mobile, before the tested artifact can be published.
