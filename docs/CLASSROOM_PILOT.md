# Field notes: five middle-school sessions

[한국어](CLASSROOM_PILOT.ko.md) · [Teaching guide](TEACHING_GUIDE.md) ·
[Try the lessons](https://chocoemong17.github.io/chainbench/papers/)

ChainBench's maintainer reports using the visual lessons in five middle-school
sessions and supplied 150 anonymous, ten-question response records. This is an
informal classroom-use case with a post-session self-report survey. It measures
perceived understanding, interest and preferences, not tested learning gains.

The survey describes the previously shown material. Backpropagation, CNN and
Dropout were subsequently refined and added; these 150 responses do not evaluate
those three new lessons. A [short bilingual project overview](https://chocoemong17.github.io/chainbench/about/)
connects the current six-lesson collection to this earlier evidence.

## How the sessions were run

The maintainer clarified that sessions 1 and 5 were led by the presenter, while
sessions 2–4 used student-led activity. Student-led includes watching a peer's
screen; it does not mean every student operated the controls. The workbook records
60 presenter-screen viewers, 30 peer-screen viewers and 60 individual operators.

The maintainer also reports favorable conversations with educators: the material
was considered worth using, but teachers needed time to understand it before
explaining it. The maintainer reports that students could follow those subsequent
explanations. These are relayed qualitative observations, not independently
documented teacher deployments, quotations or additional survey respondents.

Session dates, exact lesson coverage, attendance totals and a separate session-ID
column were not supplied in the workbook. No session-specific percentages,
response rate or comparison of teaching effectiveness is inferred from row order.

## What the responses say

The analysis maps question numbers to the ten-question questionnaire supplied for
these sessions; the workbook contains numbers rather than the full question text.
The original Korean wording and all five choices, including zero-count options,
are retained in the [aggregate record](data/classroom-survey-150.json).
An [English reading translation with all 50 choice counts](CLASSROOM_QUESTIONNAIRE.md)
helps readers inspect the instrument; it is not a separately administered English survey.

| Question and grouping | Responses | Share of 150 |
| --- | ---: | ---: |
| Q1: had never encountered the topic | 146 | 97.3% |
| Q2: felt they understood most or almost all of the explanation | 139 | 92.7% |
| Q3: found the explanation somewhat or very difficult | 19 | 12.7% |
| Q4: found the content somewhat or very interesting | 73 | 48.7% |
| Q4: neutral about interest | 39 | 26.0% |
| Q4: found the content somewhat or very uninteresting | 38 | 25.3% |
| Q5: found the film's movement somewhat or very easy to follow | 141 | 94.0% |
| Q9: wanted to learn another topic this way | 54 | 36.0% |
| Q9: were unsure about learning another topic | 85 | 56.7% |
| Q9: did not want another topic | 11 | 7.3% |
| Q10: wanted more time operating the controls themselves | 60 | 40.0% |
| Q10: preferred the current balance | 90 | 60.0% |

The most interesting component was changing graph results for 73 respondents,
everyday examples for 55, and watching the film for 22. This is a single-choice
preference, not a quality score for each component.

All 60 respondents who selected presenter-screen viewing also selected more
time operating controls. That is consistent with the maintainer's account of
different session formats. It does not establish a causal effect of interaction:
interest was positive for 30/60 presenter-screen viewers, 17/30 peer-screen
viewers and 26/60 individual operators. These were not randomized comparable
groups, and the spreadsheet alone does not explain the differences.

## What we changed in response

- Added optional, initially folded predict–try–notice activities beside the
  existing Attention and ResNet controls. They have no scoring or response collection.
- Added a bilingual preparation guide with one central idea, a control sequence,
  expected observations and a common misconception for each of the three lessons.
- Included a student-led 30-minute session route that gives each learner a turn
  and connects the demonstration to an everyday use.

The existing films, numerical examples and their limitations are retained. These
changes respond to the feedback; their impact has not yet been evaluated.

## Evidence boundaries

The source contains 150 distinct student labels, 1,500 answers in the range 1–5,
and no missing answers. Some students have identical answer patterns; those rows
were retained because matching choices do not establish duplicate participants.
The maintainer supplied the records; record validation is not independent
verification of participant identities or collection conditions.

Q1 is recalled prior familiarity, while Q2 is perceived understanding after the
session. Subtracting them would not measure a learning gain. Choice numbers are
not added into a total score. This case does not establish site-only learning,
long-term retention, repeat use or effectiveness for all middle-school students.

Only aggregate counts are included here. The student-level workbook, labels and
private conversations are outside this repository. Aggregates allow readers to
recompute the reported percentages; they do not independently verify collection.
