# Screen: two passes, reasons, shortlist

The phase takes the candidate corpus and returns every candidate decided:
included, or excluded with a reason. Apply the protocol criteria exactly as
written. Relevance-ranked sources return off-topic candidates; screening
exists to remove them, so never widen the criteria to make noisy results
fit. If the criteria feel wrong while screening, record an amendment.

## Pass 1: title and abstract

1. Run `digest` and judge its labels against the criteria.
2. Cut or keep whole kinds with the rule `digest` hands you, through
   `screen --exclude` (or `--include`, the mirror case, still bound by the
   criteria gate) with the `--on` field the digest used and
   `{"match": "<regex>", "reason": "..."}` on the pipe. The case-insensitive
   regex runs over every candidate, marks each match with `rule:<id>`, and
   stores the rule with its matched keys in the notebook, so a vocabulary
   cut is recorded as one judgment. Decided papers stay untouched: make the
   individual judgments that must survive a broad cut before running it.
   Every match takes the rule's one reason, so first list the matches with
   `show --status candidate --match <regex> --on <field>` and decide by hand
   any paper the reason misdescribes.
3. Re-run `digest` after each cut; its kinds are relative to the undecided
   set.
4. Drop to `show --status candidate` for the residue and for records you
   need in full, most-cited first. `--match` with `--on title|abstract`
   narrows by vocabulary; `--fields` with `--format tsv` keeps long listings
   cheap.
5. Decide each remaining paper include, exclude, or unsure from title,
   venue, year, and abstract alone, judging against the criteria list item
   by item. Unsure costs one full-text look later; wrongly excluded costs a
   missing paper forever, so keep unsure papers as candidates for pass 2. A
   missing abstract is a data gap: keep the paper, screen it on title plus
   landing page, or leave it unsure for pass 2.
6. Write the decisions to a JSON file and apply them with `update`. The
   script rejects an exclusion without a reason.

<example for="decisions">
{
  "doi:10.1234/example.1": {"status": "included"},
  "arxiv:2401.00001": {"status": "excluded",
                       "reason": "no generation component (criterion 1)"},
  "title:some borderline paper": {"status": "excluded",
                                  "reason": "editorial, not a study"}
}
</example>

## Exclusion reasons

Use a short reason naming the failed criterion, and keep reasons consistent
across the batch. Recurring kinds: off-topic, wrong publication form,
outside year window, language, superseded duplicate, inaccessible (no
abstract and no reachable text). A preprint and its journal version can
enter the corpus under different DOIs; when both survive screening, keep the
citable version and exclude the other as "superseded duplicate".

## Pass 2: full-text triage

For the remaining unsure papers, fetch what the record links (`pdf_url`,
`landing_url`), skim introduction and conclusions, and decide. Exclude a
paper whose text is unreachable at all with reason "inaccessible" at lite
and full; at ultra, note it in the report as identified but unassessed.

## Shortlist size

The included set drives extraction cost. Lite: 5 to 10 papers. Full: 10 to
25. Ultra: whatever the criteria admit; if that exceeds roughly 40, say so
and agree with the user on tighter criteria or a longer run before
proceeding. Fewer than 5 included papers usually means search coverage
failed: reopen search before concluding the field is empty.

## Bias sweep

After screening, check the included set for concentration: one author group,
one venue, or one year dominating is a signal to search the neglected
directions.
