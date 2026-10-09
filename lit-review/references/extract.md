# Extract: reading, records, appraisal

Phase takes included papers; returns, for each, one extraction record on pad
and `read_level` set with `set`. Synthesis reads records; anything missing
from them needs re-read later.

## Reading order and depth

- Start with anchor: included paper most cited by the others.
- Read each paper's `pdf_url` with `/read-pdf`; its page markers become
  claim locations in extraction record. No PDF reachable: fall back to
  landing page's HTML text, then abstract as floor.
- After each paper, set its `read_level` (`abstract` or `full-text`) with
  `set`. Invariant 5 makes this label the ceiling for how its claims appear
  in report.
- Read survey among included papers for its own claims and reference list;
  per invariant 5, cite its summaries of other papers as survey's
  characterization, never as those papers.

## Extraction record

Write one record per paper; `status` and `brief` list included papers with
no extraction entry. Fill only what source states; write "not reported" for
rest. Body free beyond `type` and `key`: add per-paper hypothesis-directed
questions whenever argument needs them.

<template for="extraction">
$R write "$S" <<'JSON'
{"type": "extraction", "key": "doi:10.1234/example.1",
 "claims": "the one to three findings the paper itself asserts, each with location",
 "method": "design, dataset or sample, baselines compared against",
 "evidence": "the numbers backing each claim, as reported, with units",
 "limitations": "those the authors state; then the reviewer's, labeled",
 "relation": "which corpus papers it builds on, contradicts, or replicates",
 "quote": "at most one verbatim sentence worth citing exactly, with location",
 "appraisal": "one judgment per Quality appraisal dimension, never summed"}
JSON
</template>

## Quality appraisal

Appraise while reading, one judgment per dimension, weighed together, never
summed into one score:

| Dimension | Question |
| --- | --- |
| Method | Does design test claim? |
| Data | Sample or dataset adequate and appropriate? |
| Review status | Peer-reviewed, or preprint (label, do not penalize)? |
| Reproducibility | Code, data, or protocol available? |
| Consistency | Numbers in text, tables, abstract agree? |
| Independence | Funding or affiliation bearing on claim? |

Full: appraisal shapes how much weight paper carries in synthesis, mentioned
where it matters. Maximum: report carries table for every included paper.

## Parallel extraction

Delegate through `/summon divide`, one delegate per included paper. Each
brief: evidence is paper's corpus entry and its `pdf_url`; rules are reading
order and depth above, `/read-pdf` as reader; contract is extraction
template, output as JSON object alone. Delegates write no session state;
lead judges each output, then runs `write` and `set` itself, so branch
leaves no trace in deliverable.
