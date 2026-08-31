# Extract: Reading, Records, Appraisal

Turn each included paper into one extraction record. The records, not the
papers, are what synthesis reads; anything not captured here is not
available later without re-reading.

## Reading order and depth

- Start with the anchor: the included paper most cited by the others; it
  fixes the field's vocabulary and baseline claims.
- Read each paper's `pdf_url` with `/read-pdf`; its page markers become
  the claim locations in the extraction record. When no PDF is reachable,
  fall back to the landing page's HTML text, then to the abstract as the
  floor. After each
  paper, set its `read_level` (`abstract` or `full-text`) with `update`.
  Invariant 5 makes this label the ceiling for how its claims appear in the
  report.
- A survey among the included papers is read for its own claims and its
  reference list; per invariant 5, its summaries of other papers are cited
  as the survey's characterization, never as those papers.

## Extraction record

One record per paper, jotted onto the session pad so coverage stays
checkable: `status` and `brief` list included papers with no extraction
entry. Fill only what the source states; write "not reported" rather than
inferring. The body is free beyond `kind` and `key`: add per-paper
hypothesis-directed questions whenever the argument needs them, and the
jot advisory warns on a key the corpus lacks.

<extraction_record>
$R jot "$S" '{"kind": "extraction", "key": "doi:10.1234/example.1",
  "claims": "the one to three findings the paper itself asserts, each with location",
  "method": "design, dataset or sample, baselines compared against",
  "evidence": "the numbers backing each claim, as reported, with units",
  "limitations": "those the authors state; then the reviewer's, labeled",
  "relation": "which corpus papers it builds on, contradicts, or replicates",
  "quote": "at most one verbatim sentence worth citing exactly, with location"}'
</extraction_record>

## Quality appraisal

Appraise while reading, one judgment per dimension, weighed together
rather than summed into a score to rank by:

| Dimension | Question |
| --- | --- |
| Method | Does the design actually test the claim? |
| Data | Is the sample or dataset adequate and appropriate? |
| Review status | Peer-reviewed, or preprint (label, do not penalize)? |
| Reproducibility | Code, data, or protocol available? |
| Consistency | Do the numbers in text, tables, and abstract agree? |
| Independence | Funding or affiliation that bears on the claim? |

At full, appraisal shapes how much weight a paper carries in synthesis and
is mentioned where it matters. At ultra, the report carries the table for
every included paper. Title-mismatch signals are handled at verification,
per `report`.

## Parallel extraction

With sub-agents available and more than roughly eight full-text papers, fan
out: one worker per paper, input the record template plus the paper's corpus
entry, output one extraction record. The orchestrator alone runs `update`
and `jot`; workers never write session state. Worker output follows the
same template so the branch leaves no trace in the deliverable.
