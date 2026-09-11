# Friction log and review findings

Written as things happened, not reconstructed afterwards. Times are approximate.

## What cost us time

**Tesseract never installed. ~15 minutes, and it could have been the whole day.**
The obvious OCR choice needs a system binary. The winget install produced no output for over ten
minutes while the clock ran. We stopped waiting and switched to RapidOCR, which installs with pip,
carries its own ONNX models and needs no binary. It read a sublimit table correctly on the first
attempt. The switch also improved the deliverable: the one-command install is now genuinely one
command, with nothing to install outside the Python environment.
*Lesson: in a timeboxed build, prefer a dependency you can install from inside your package manager
over the one with the better reputation.*

**OCR ran at 14 seconds per page, and naive parallelism made it worse. ~25 minutes.**
226 pages at 14s is 48 minutes of a four-hour budget. Spreading the work over six worker processes
changed nothing, because onnxruntime grabs every core per instance by default, so six workers meant
dozens of threads fighting over sixteen logical cores. Measured throughput actually fell, to 0.07
pages per second. Capping threads per worker and dropping the render from 300 to 200 DPI got it
moving. The fix that mattered most was ordering pages shortest-document-first, so an interrupted
run still covers eighteen of nineteen documents instead of most of one.
*Lesson: measure the parallel version before trusting it. We assumed a speedup and lost twenty
minutes to a slowdown.*

**One model call per candidate page took 112 seconds for a four-page document.**
Nineteen documents at that rate does not fit the day. Batching all matched snippets for a question
into a single call per document cut it to 68 seconds and improved the answers, because the model
sees the whole picture for a question rather than one page at a time.

**A prompt that was too strict caused a false negative on the bar we committed to.**
Our offshore prompt said that mentions of transport or cargo do not count as offshore. The first
offshore document we tested is a transport policy whose cover items include "Offshore Cancellation
Costs". The model dutifully talked itself out of the right answer. Removing the over-constraint
fixed it.
*Lesson: negative instructions in a prompt are as dangerous as missing ones, and only a labelled
test set catches it.*

**OCR runs words together, which silently broke our search.**
The strongest offshore evidence in one document reads
`Inrespectofallbelowsealeveloffshoreinterarraycableworks`. Every regex with a word boundary missed
it. We now match against both the raw text and a de-spaced copy. This would have been invisible
without reading the OCR output by hand.

## Incidents

**A customer-internal document was committed and pushed to a public repository.**
The use-case document describing the If Industrial pilot, including a policy reference, was staged
by a blanket `git add -A` and pushed. It had been flagged one message earlier as needing a decision
about whether it belonged in the repository, and then swept in anyway. The repository is public.
It was removed from the tree within about three minutes and the team decided not to rewrite history.
The source PDFs were never at risk, because `data/` had already been ignored.
*Root cause: a blanket add in a repository containing files that were deliberately left untracked.*

**The OCR cache was one command away from the same fate.**
`cache/` holds the extracted text of every source document, which is the same content as the PDFs
in a different shape. It was not ignored. Caught before anything was committed, but only by
checking rather than by anything preventing it.

## Review findings, before the demo

- **The insured name is often unrecoverable.** These documents are partially redacted, and the
  policyholder name sits behind a black box. The model returns a customer number instead. Grouping
  layers by insured, which question three asks for, is weakened by this and the app has to fall
  back to the policy number.
- **Figures for questions two and three are unverified.** A misread digit is a wrong answer by the
  customer's own definition. We did not have time to hand-check every extracted amount, and we say
  so on the demo rather than implying otherwise.
- **Ground truth is assumed, not confirmed.** Scoring treats folder membership as correct. A
  document in `Projects` could legitimately also be offshore, which would show up as a false
  positive that is actually right.

## One automation for the next iteration

**A pre-commit hook that refuses to stage anything under `data/` or `cache/`, or any document
format, regardless of what the gitignore says.**

Both incidents above came from the same root: the safety of the repository depended on a person
remembering the rule at the moment of committing. Today that rule failed once and nearly failed
twice, and the only thing that caught the second case was someone going back to check. A hook moves
the guarantee from attention to enforcement, costs about ten lines, and would have prevented the
one incident that actually reached a public remote.
