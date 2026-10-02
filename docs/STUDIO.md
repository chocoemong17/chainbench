# Choose, compute and read in a browser

The development `studio` command adds new computation to the existing offline
reports. Choose a problem family, change its conditions, select methods and press
**Run a new experiment**. Python generates actual numeric inputs and computes
their trajectories. The embedded report shows the arrays, start, reference,
three metrics and every actual update. Downloaded reports remain readable after
the server stops.

This command is in development source after v0.6.0. The frozen v0.6.0 wheel and
reading ZIP do not include it. From an environment with the current source
installed, run:

```bash
chainbench studio --lang ko
```

Open the full loopback URL printed in that terminal on the **same computer**.
The server chooses an available port. It does not open a browser automatically.
`--lang en` selects English; the page also has a language switch. Stop with the
page's **Stop server** button or Ctrl+C. The default idle expiry is 900 seconds;
`--idle-timeout` accepts 10–3600 seconds. `--port` can select a local port, with
zero retaining automatic selection. There is no public-host option.

The URL contains a fresh session key in its fragment. The page removes the
fragment from history after reading it and holds it only in memory. Reloading
the page loses that key: reopen the full terminal URL. A saved HTML report
contains neither the key nor a live server connection.

## Three questions to explore

| Question | Controls | What to inspect |
| --- | --- | --- |
| How does a stretched quadratic affect the methods? | Fix seed and L; change condition number from 10 to 100 | Gap and stationarity, followed by the exact iterates; the actual matrix and reference are visible |
| How does the sparsity penalty change the solution? | Select diagonal LASSO; fix seed; vary λ from 0 to 0.3 | The analytic reference, ISTA/FISTA updates and proximal-gradient stationarity |
| How does moving toward a vertex differ from unconstrained movement? | Select simplex; change dimension and seed | Frank–Wolfe's recorded coordinates, simplex feasibility and its family-specific gap |

Use several seeds. Each changes the arrays and start; no claim rests on a single
favorable example. The seed is descriptive metadata after generation; saved
arrays are the authority for reruns. The methods use their existing documented
default parameters. Equal update counts are not equal computational work.

Changing any form input hides the old result and revokes its download links.
Each completed result retains the exact settings actually sent, so a visible
curve cannot silently acquire the next experiment's label. The method selector
inside the report inspects already computed rows; **Run a new experiment** is
the action that performs fresh computation. CG can stop before the requested
update budget.

## Keep and rerun the result

- **Input JSON** retains the sealed numeric arrays, x0, settings and hashes.
- **Result JSON** retains those inputs, environment and every computed row.
- **Standalone HTML report** contains the same result, plots and offline controls.

The server writes none of these files. Downloading saves them through the
browser. Current downloads remain available after explicit server shutdown.
JSON downloads retain the original Python serialization, including signed zero
and float representations used by the sealed hashes. The browser does not
parse and reserialize those download bytes.
For an exact-input rerun, use the development CLI:

```bash
chainbench instance replay studio-result.json --format html --lang ko --output replay.html
```

See [the complete numeric-input and replay contract](STORED_INPUTS.md). The studio
does not add an array editor, arbitrary file import, public hosting, data upload
to GitHub or comparison of different objectives on a shared scale. Those are
distinct from its narrow parameter-driven teaching workflow.

## Local service contract

The listener binds IPv4 **127.0.0.1 only**. It serves exactly `/`, `/api/run` and
`/api/shutdown`; it is not a directory/file server. No cookies, telemetry,
external assets, user-controlled commands, code, URLs or file paths are accepted.
It adds no package dependency beyond existing NumPy and Python's standard library.

Every request requires the exact loopback Host with its selected port. An
Origin header, when present, must exactly match that origin. POST additionally
requires that Origin and a constant-time comparison with the session token in
`X-ChainBench-Token`. Duplicate security headers and cross-site Fetch Metadata
are rejected; no CORS permission is returned. The printed key is a local session
boundary, not authentication against another process with access to the account.

POST accepts one JSON body, a single decimal Content-Length and exactly
`application/json`. It rejects transfer/content encodings, Expect, duplicate
length/type headers, missing fields, unknown keys, duplicate JSON keys, booleans
in numeric fields, non-finite numbers and unsupported methods. The UI request
object contains family, dimension, seed, steps, methods and language, plus only
the selected family's parameters.

| Resource | Limit |
| --- | --- |
| Request body | 1–4,096 bytes, before JSON parsing |
| Dimension | Integer 2–16 |
| Updates per method | Integer 0–200 |
| Seed | Integer 0–2³²−1 |
| Methods | Distinct subset of the selected family's existing methods |
| Quadratic L; condition number | 0.001–1,000; 1–10,000 |
| LASSO λ | 0–10 |
| Socket reads/writes | 3-second inactivity timeout |
| Computation | One fixed child process at a time, 20-second communication timeout |
| Encoded response | At most 8,000,000 bytes |

The shared numeric core also enforces its work and recorded-scalar budgets.
The worker uses one BLAS thread, runs the installed module through the current
Python interpreter without a shell, and is killed and reaped on timeout. A failed
calculation returns an error, never a successful empty plot. The service serializes
requests; Stop waits for a running request to finish or time out. This is an input,
work and time bound, not an operating-system memory sandbox or production server.

Responses prohibit caching, framing of the control page and external resources.
The computed report sits in a sandboxed frame that can run its own offline
controls and downloads but cannot read the parent session. No requests or bodies
are logged. The server does not persist experiments or write report files.

Implementation references: Python's [HTTP server interfaces and limitations](https://docs.python.org/3/library/http.server.html)
and [subprocess timeout/cleanup contract](https://docs.python.org/3/library/subprocess.html).
The application adds the origin, token, protocol, resource and lifecycle checks;
the standard HTTP handler alone does not supply those boundaries.

## Verification on GitHub

Regression tests exercise actual loopback requests, invalid framing/origins/tokens,
pre-computation input rejection, a genuinely timed-out child and its cleanup,
recovery, socket timeout, idle expiry, fresh session keys and explicit shutdown.
Actual generated records are rerun and deliberately damaged records are rejected.

Both clean wheel and sdist installations start their own installed studio outside
the checkout. Six cases (three families × seeds 0 and 7) independently recompute
input bytes, hashes and every row's objective, gap, stationarity and reference
distance using standard-library scalar arithmetic. They match exact embedded
HTML records, check eight rejected requests, shutdown, absence of server-created
files and absence of session material. Publication requires every typed outcome
for both distributions. A targeted fault injection removes that gate and must
be detected by its regression.

The real Chromium script submits the six cases at 1440px and 390px, changes methods,
checks keyboard-selected actual rows and exact downloads, stops the server and
downloads again. It reads the saved reports offline with and without JavaScript,
checks the no-script control-page fallback, and renders a two-page review PDF.
The `studio-review-<commit>` Actions artifact retains the outputs and source-bound
proof. Generated files and full verification run on GitHub Actions; the local
project remains under its 1 GB cap.

The numerical claims and recurrences remain those in [SOURCE_MAP.md](SOURCE_MAP.md).
Finite observations, hashes and rerun agreement do not prove a theorem, authenticate
an author or establish outside adoption.
