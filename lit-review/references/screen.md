# Screen: Two Passes, Reasons, Flow Counts

Screening applies the protocol criteria to the corpus, exactly as written.
If the criteria feel wrong while screening, record an amendment (owned by
`protocol`).

## Pass 1: title and abstract

Start from `digest`, which returns the kinds of candidate in the corpus
rather than the rows: one label, one count, one selecting rule, and two
exemplars each. Judge the labels, cut or keep whole kinds with the rule the
digest hands you, then re-run `digest` on what remains, since the labels are
relative to the undecided set. Drop to `show --status candidate` for the
residue and for records you need in full; most-cited first; `--match` with
`--on title|abstract` narrows by vocabulary, and `--fields` with
`--format tsv` keeps long listings cheap. For each paper decide include,
exclude, or unsure from title, venue, year, and abstract alone.

- Judge against the criteria list, item by item.
- Unsure costs one full-text look later; wrongly excluded costs a missing
  paper forever. Keep unsure papers as candidates for pass 2.
- A missing abstract is a data gap: check the landing page before deciding.

Write decisions to a JSON file and apply them with `update`. The script
rejects an exclusion without a reason and applies nothing until the whole
batch is valid.

<decisions_example>
{
  "doi:10.1234/example.1": {"status": "included"},
  "arxiv:2401.00001": {"status": "excluded",
                       "reason": "no generation component (criterion 1)"},
  "title:some borderline paper": {"status": "excluded",
                                  "reason": "editorial, not a study"}
}
</decisions_example>

## Bulk rules

A vocabulary cut over hundreds of candidates is one judgment, and the
record should say so. `screen --on title --match "<regex>" --exclude
--reason "..."` applies a case-insensitive regex to every candidate, marks
each match with `rule:<id>`, and stores the rule with its matched keys in
the notebook, so flow counts trace to the predicate that produced them.
Decided papers stay untouched: make the individual judgments that must
survive a broad cut before running it. `--include` exists for the mirror
case, still bound by the criteria gate.

## Exclusion reasons

Use a short reason naming the failed criterion. Recurring kinds: off-topic,
wrong publication form, outside year window, language, superseded duplicate
(preprint vs journal version: keep the citable one), inaccessible (no
abstract and no reachable text). Reasons feed the report's flow counts, so
keep them consistent across the batch.

## Pass 2: full-text triage

For remaining unsure papers, fetch what the record links (`pdf_url`,
`landing_url`), skim introduction and conclusions, and decide. Papers whose
text is unreachable at all are excluded with reason "inaccessible" at lite
and full; at ultra, note them in the report as identified but unassessed.

## Shortlist size

The included set drives extraction cost. Lite: 5 to 10 papers. Full: 10 to
25. Ultra: whatever the criteria admit; if that exceeds roughly 40, say so
and agree with the user on tighter criteria or a longer run before
proceeding. Fewer than 5 included papers usually means search coverage
failed: reopen search before concluding the field is empty.

## Bias sweep and flow counts

After screening, check the included set for concentration: one author group,
one venue, one year dominating is a signal to search the neglected
directions. Then derive the flow from state: `status` gives
per-status counts, the log gives per-search totals. The report template in
`report` carries the counts block: identified, deduplicated, screened out at
pass 1, screened out at pass 2, included.
