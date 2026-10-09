# Screen: two passes, reasons, shortlist

Phase takes candidate corpus; returns every candidate decided: included, or
excluded with reason. Apply protocol criteria exactly as written.
Relevance-ranked sources return off-topic candidates; screening exists to
remove them, so never widen criteria to make noisy results fit. Criteria
feel wrong while screening: record change.

## Pass 1: title and abstract

1. Run `digest`; judge its labels against criteria.
2. Cut or keep whole types with rule `digest` hands you, through
   `screen --exclude` (or `--include`, mirror case, still bound by criteria
   gate) with `--on` field digest used and
   `{"match": "<regex>", "reason": "..."}` on pipe. Case-insensitive regex
   runs over every candidate, marks each match with `rule:<id>`, stores rule
   with its matched keys in notebook, so vocabulary cut is recorded as one
   judgment. Decided papers stay untouched: make individual judgments that
   must survive broad cut before running it. Every match takes rule's one
   reason, so first list matches with
   `show --status candidate --match <regex> --on <field>` and decide by hand
   any paper the reason misdescribes.
3. Re-run `digest` after each cut; its types are relative to undecided set.
4. Drop to `show --status candidate` for residue and for records you need in
   full, most-cited first. `--match` with `--on title|abstract` narrows by
   vocabulary, `--on key` by key prefix, `--found-by` by `find` that fetched
   paper; `--fields` with `--format tsv` keeps long listings cheap.
5. Decide each remaining paper include, exclude, or unsure from title,
   venue, year, abstract alone, judging against criteria list item by item.
   Unsure costs one full-text look later; wrongly excluded costs missing
   paper forever, so keep unsure papers as candidates for pass 2. Missing
   abstract is data gap: run `fill` to look it up in other indexes; none has
   it: keep paper, screen on title plus landing page, or leave unsure for
   pass 2.
6. Write decisions to JSON file, apply with `set`. Script rejects exclusion
   without reason. Give each exclusion `stage` of pass that made it,
   `title-abstract` here; `status` counts exclusions by stage for report's
   flow counts; `screen` sets stage itself.

<example for="decisions">
{
  "doi:10.1234/example.1": {"status": "included"},
  "arxiv:2401.00001": {"status": "excluded",
                       "reason": "no generation component (criterion 1)",
                       "stage": "title-abstract"},
  "title:some borderline paper": {"status": "excluded",
                                  "reason": "editorial, not a study",
                                  "stage": "title-abstract"}
}
</example>

## Exclusion reasons

Short reason naming failed criterion, consistent across batch. Recurring
kinds: off-topic, wrong publication form, outside year window, language,
superseded duplicate, inaccessible (no abstract and no reachable text).
Preprint and its journal version can enter corpus under different DOIs; both
survive screening: keep citable version, exclude other as "superseded
duplicate".

## Pass 2: full-text triage

Remaining unsure papers: fetch what record links (`pdf_url`, `landing_url`),
skim introduction and conclusions, decide with `"stage": "full-text"` on
each exclusion. Text unreachable at all: exclude with reason "inaccessible"
at basic and full; at maximum, note in report as identified but unassessed.
Before excluding paper as inaccessible, run `fill` on its key.

## Shortlist size

Basic: 5 to 10 papers. Full: 10 to 25. Maximum: whatever criteria admit;
exceeds roughly 40: say so, agree with user on tighter criteria or longer
run before proceeding. Fewer than 5 included papers usually means search
coverage failed: reopen find before concluding field is empty.

## Bias sweep

After screening, check included set for concentration: one author group, one
venue, or one year dominating signals search of neglected directions.
