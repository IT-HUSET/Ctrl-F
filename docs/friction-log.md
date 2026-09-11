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

## Late finding: the folders are a search set, not an answer key

We scored against folder membership, assuming a document in `excess auto liability` is a document
that has excess auto cover. Checking a false negative by hand showed otherwise. The document is a
Liability Master policy for Danfoss whose entire text contains the word "auto" once, in "Products
Recall - auto parts", and the word "excess" once, in "excess of deductible". There is no auto
liability cover in it.

Re-reading the customer note explains it: they offered "supporting documents to search through,
perhaps 15-20 documents per use case". The folder is the haystack for a question, not the set of
needles. Documents that legitimately do not match are supposed to be in there, because finding
nothing in them is part of the task.

So precision and recall against folders are a proxy, and a weak one for questions two and three.
The proxy holds better for offshore, where every document checked by hand in that folder does carry
offshore wording. We report the numbers with that caveat attached rather than dropping them,
because the alternative is having no measure at all.

*This is the finding we would most want to have had at 13:10 rather than 16:00. It came from
reading one failing case by hand, which is the cheapest review technique we used all day.*

## Final result, full corpus

All 19 documents, 226 pages, OCR complete.

| Question | Precision | Recall | Unexplained false positives |
| --- | --- | --- | --- |
| Offshore | 0.83 | 1.00 | 0 |
| Excess auto, US | 1.00 | 0.50 | 0 |
| Layer | 0.80 | 1.00 | 0 |

There are no unexplained false positives anywhere. Both documents the score counts as wrong were
read by hand and are correct: one carries "for off-shore GBP 5,000,000", the other "cover is MNZD10
in excess of MNZD20". Both sit in the excess-auto folder, which is a search set for a different
question, so the score penalises the system for being right.

Layer recall went from 0.25 to 1.00 on one change: removing the word boundary from the pattern. OCR
writes "Captivelayer" and "excesspolicy", so the boundary made a whole class of evidence invisible.
The same root cause had already bitten us once on offshore, and we still did not generalise the fix
the first time.

The three remaining excess-auto misses were checked. Two are the Danfoss Liability Master, whose
entire text contains the word "auto" once, in "Products Recall - auto parts", and no auto liability
cover at all. The third is scoped to Europe. All three are correct rejections that the folder proxy
counts as failures, which means true recall on that question is higher than 0.50 and we cannot say
by how much without the customer confirming the answer key.

We also learned the vocabulary matters more than the model: the phrase "excess auto" appears nowhere
in the corpus. These policies say "Use of Motor Driven Vehicles - Fleet of Vehicles".

## Late additions: free-text and semantic search

Both were requested after the PRD was agreed. Each time, the PRD was updated in the same change,
because "demo aligns with PRD" is scored and a demo showing something the PRD calls out of scope
loses points for a feature that should win them.

**Question words broke free-text search, invisibly.** Searching "what is the debris removal limit"
ranked pages full of "the" above the page holding the figure, and the model correctly answered that
it could not find a limit. Dropping stopwords changed the answer to EUR 7 000 000 with a page
citation, matching the figure verified by eye at 14:30. The lesson is that the model behaved
honestly throughout; the retrieval was what lied.

**We hedged the embedding model download rather than waiting on it.** The multilingual model is
1.2 GB and the Tesseract experience earlier in the day had already shown what an unattended download
can cost. We pulled the smaller English-centric model in parallel and made the code use whichever
was installed. The larger one arrived, so the hedge cost 274 MB and bought certainty.

## Found while restyling, before the demo

**The documented one-command run was broken on the remote.** An earlier patch script wrote the run
command inside a Python string, where backslash-r is an escape sequence. It became a carriage
return, so both the README and `CLAUDE.md` showed a lone dot followed by `un.ps1`. Anyone copying
the command from the README would have failed the deliverable that says runnable with one command.
Found by reading file bytes, and repaired with a script built from byte values so no escape sequence
could reproduce it.
*Lesson: keep Windows paths out of escape-processing strings, and check committed docs by bytes.*

**The one-command run was quietly phoning home.** Our own Streamlit log printed "Collecting usage
statistics". Every manual test had passed a flag to switch that off, but `run.ps1` did not, so the
real demo path broke the promise that nothing leaves the machine. The switch now lives in
`.streamlit/config.toml`, where every launch picks it up.

**A 200 is not proof you got the file.** The first theme loaded its fonts through Streamlit's static
file route, and a check of the font URL returned 200. The page still rendered in plain serif. The
headers showed why: the 200 carried `text/html` and 7459 bytes, the app's own page, not a font. The
fonts are now embedded in the stylesheet. It is the lesson the empty-text PDFs taught this
afternoon: verify the content, not the status.
