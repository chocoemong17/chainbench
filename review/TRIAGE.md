# Handling actual outside reports

This is a procedure, not a claim that reports have arrived. Use [issue #28](https://github.com/chocoemong17/chainbench/issues/28)
for real attempts. Do not create fictional success stories, use alternate accounts
as reviewers, or count automated runs as users. A successful tool result is not
identity verification, independent review or an endorsement.

## First response

Thank the reporter for the specific observation. Check the release, exact command,
software versions and public synthetic config. Do not ask for passwords, API keys,
unpublished research or machine/home paths. Request a reduced example only when
necessary; never request a whole environment dump. Let people use pseudonyms.

## Decide what kind of report it is

| Evidence | Next action |
|---|---|
| Installation failed before experiments | Reproduce the package/environment issue; do not classify the numerical algorithm as wrong yet |
| Helper exits 2 | Identify the missing/invalid field or wrong install; do not call it a passing review |
| Helper exits 3 | Compare the generated input fingerprints and numerical differences; close values do not establish identical inputs |
| Helper exits 1 | Inspect the first differing row/metric/termination. Near a CG threshold, stopping on a different update may be legitimate |
| Same inputs, materially wrong iterate/gap | Reduce to a tiny fixture, independently compute the expected value and add a failing regression before fixing |
| Results match but documentation is confusing | Fix the onboarding text or explanation; record the concrete misunderstanding |
| Successful attempt | Link the original report accurately, without turning it into an endorsement or overstating adoption |

## Confirm before changing claims

For a bug, record the original release and a test that fails before the fix and
passes after it. Keep the old release intact and publish a new version only for
an actual change requiring distribution. For a portability difference, record
which bytes/versions differ and the comparison tolerance. Do not widen tolerances
just to get a match or discard inconvenient reports.

For any public summary, separate the reporter's statement from the maintainer's
reproduction. A single comment may not establish independence; CI downloads,
maintainer downloads, forks and stars are not active-user counts. Preserve source
links and uncertainty. There is no minimum number of positive reports required.

No automated reply, outreach, telemetry, subscription or spending is enabled by
this guide. Agree on the destination and message before contacting outside groups.
