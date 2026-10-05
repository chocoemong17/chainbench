# Add a visual lesson: concept first

[한국어](LESSON_AUTHORING.ko.md) · [Brief template](templates/LESSON_BRIEF.md)

The public collection currently has **three finished lessons**: Adam, Attention
and ResNet. Backpropagation, CNN and Dropout are **unapproved concepts**, available
on the `study/learning-foundations` review branch. They are not six finished lessons.

1. Copy the brief template into `docs/reviews/<topic>/BRIEF.md`. Cite the primary
   paper and choose one concrete mechanism; a landscape plot suits an optimizer,
   but does not automatically explain a neural-network architecture.
2. Declare a small example, what changes, what stays fixed, and what it cannot
   prove. Verify displayed numbers using an independent calculation. For example,
   [the foundations fixtures](../review/learning_foundations_v2.py) check gradients
   against finite differences and compare the complete convolution with its unrolled matrix.
3. Prepare as many plain scenes as the mechanism needs. Use one sentence per scene, English by default,
   equivalent Korean, and still images alongside a slow storyboard. No finished
   video is required. The [filled brief](reviews/learning-foundations/BRIEF.md)
   shows the exact scope and variable-length plans for this round.
4. Run the branch's focused Actions workflow and inspect every scene in both
   languages. Share the GitHub-rendered review README; the reviewer needs no ZIP,
   local Python or Actions artifact download. Record requested changes and the
   revision approved. Do not interpret numeric correctness as teaching approval.
5. After owner approval, implement the film, two interactions and paper link using
   the existing lesson format. `web/papers/shared/lesson.js` contains existing
   lesson behavior; `scripts/render_visual_papers.py` renders Attention/ResNet;
   `scripts/check_visual_papers_browser.py` demonstrates browser verification.
   These are existing examples, not a claim that adding a lesson is one config edit.
6. Open a coherent PR, run appropriate numeric and browser checks and all required
   CI, then validate main. Website publication uses only the existing gated
   `pages.yml`; review-branch images never deploy the production site.

The concept workflow pins Pillow and renders in GitHub Actions. Locally only edit
small sources; reuse the shared program directory if any local tool is needed.
The generated review bundle is capped at 12 MB per revision and GitHub retains it on the review
branch. Do not add dependencies, media caches, private student data or paper PDFs.

Feedback belongs in the [feedback-to-change record](FEEDBACK_ACTIONS.md).
Use the owner's actual words or a labeled paraphrase, link the observed change,
and distinguish implemented, proposed and awaiting review. Do not imply that a
change was subsequently tested by students unless that follow-up happened.
