---
name: draft-paper
description: >-
  Drafts conference, workshop, journal, survey, or demo papers with an
  evidence ledger, verified citations, adversarial review, and rebuttals.
  Use when turning an idea or results into a submittable draft, retargeting
  a draft, or answering reviews.
license: MIT
compatibility: >-
  Network access is needed for CFP verification and literature retrieval;
  without it, venue facts ship flagged as unverified.
metadata:
  argument-hint: "[design|build|refactor|rebut] [short|full|workshop|journal|survey|demo]"
---

# Draft Paper

Turn research at any stage into a submittable paper draft, or answer its
reviews. The verb (what to do) and the format (what to produce) route each
run. The pipeline is one sequence; each verb enters and exits it at fixed
stages.

## Registry

| Name | Path |
| --- | --- |
| `award-assessment` | [references/award-assessment.md](references/award-assessment.md) |
| `award-patterns` | [references/award-patterns.md](references/award-patterns.md) |
| `citation-report-template` | [references/citation-report-template.md](references/citation-report-template.md) |
| `design-plan-template` | [references/design-plan-template.md](references/design-plan-template.md) |
| `evidence-ledger-template` | [references/evidence-ledger-template.md](references/evidence-ledger-template.md) |
| `gate-protocol` | [references/gate-protocol.md](references/gate-protocol.md) |
| `help` | [references/help.md](references/help.md) |
| `outline-template` | [references/outline-template.md](references/outline-template.md) |
| `rebuttal-mapping-template` | [references/rebuttal-mapping-template.md](references/rebuttal-mapping-template.md) |
| `rebuttal-playbook` | [references/rebuttal-playbook.md](references/rebuttal-playbook.md) |
| `reviewer-checklist` | [references/reviewer-checklist.md](references/reviewer-checklist.md) |
| `run-template` | [references/run-template.md](references/run-template.md) |
| `section-guide` | [references/section-guide.md](references/section-guide.md) |
| `trace-schema` | [references/trace-schema.md](references/trace-schema.md) |
| `venue-brief-template` | [references/venue-brief-template.md](references/venue-brief-template.md) |
| `venue-standards` | [references/venue-standards.md](references/venue-standards.md) |

## Scripts

One command verifies the run trace. Bind it once per shell and re-bind after
a reset; `realpath` is required.

<commands>
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-draft-paper"
$R trace verify <run-dir>
</commands>

On success, `trace verify` prints one JSON document on stdout and exits 0:
`{"run_id": "<slug>", "events": N}`. Stderr `signal:` lines are advisory.
On any defect it exits 1 and names the first one, with its line number when
the defect sits on a line. This command surface is the handoff point:
invoke it and read its output; read the source only when troubleshooting on
the user's instruction.

## Verbs

| Verb | Starts from | Runs stages | Delivers |
| --- | --- | --- | --- |
| `design` | spark or shaped idea | 1-2 | positioned research plan |
| `build` | shaped idea, partial or full results | 2-8 | complete draft |
| `refactor` | existing draft | 3-8, abbreviated | draft retargeted to a new format or venue, claims preserved |
| `rebut` | reviews received | 9 | rebuttal or revision letter |
| `help` | any | none (one-shot) | dispatch card; changes nothing |

Dispatch by explicit verb, then by request shape (rough idea: `design`;
results: `build`; reviews: `rebut`), then by the default verb `build`.

## Input states

| State | Means | Handling |
| --- | --- | --- |
| spark | a few sentences of idea | `design` positions it; nothing is written as fact. |
| shaped | hypothesis plus literature context or early evidence | `design` sharpens the plan; `build` starts a partial ledger. |
| partial results | some experiments done | `build` ledgers what exists, marks the rest TO-RUN, and states only what ran. |
| full results | complete artifact set | `build` runs the full pipeline. |
| existing draft | a draft to retarget; `refactor` only | Re-outline against the new format and venue checklist; keep unchanged sections. |

If the state is ambiguous, ask exactly one question.

## Formats

Each format's section structure is its section in `section-guide`.

| Format | Typical shape |
| --- | --- |
| `short` | 6-page idea paper (HotNets/HotOS/HotStorage style) |
| `full` | conference full paper; page budget from the CFP |
| `workshop` | 4-6 pages, preliminary work |
| `journal` | extended, no hard cap, revision rounds |
| `survey` | taxonomy and gaps, no novel experiments |
| `demo` | 2-4 pages plus a live artifact |

If the format is unknown, ask exactly one question. Defaults: `full` for
results, `short` for a spark with a strong contradiction.

## Pipeline

0. Intake: detect state and verb; confirm format. Record the target venue
   (if unknown, ask), the backbone model version (pin it; reliability
   assumptions do not transfer across models), and artifact paths. Create
   the run directory: `<run-dir>/RUN.md` from `run-template`, and
   `<run-dir>/TRACE.jsonl` seeded with a `run-started` event per
   `trace-schema`. Study the current CFP per `venue-standards`; record the
   cycle year and source URLs in the venue brief (`venue-brief-template`),
   and fetch the venue's LaTeX template now.
1. Positioning (`design`; `build` validates it for shaped inputs): sweep
   the literature via retrieval APIs; analyze the gap; argue novelty from
   retrieved full text; state falsifiable claims; write a
   pre-registration-style experiment plan. Write the design plan
   (`design-plan-template`): a concrete scenario sketch that passes the
   practitioner-recognition test, the contradiction framing
   (`award-patterns` 1), a worked numerical example of the core mechanism,
   and the award assessment (`award-assessment`). Gate: the human approves
   the plan per `gate-protocol`.
2. Evidence: build the evidence ledger (`evidence-ledger-template`). Every
   quantitative claim maps to an artifact file and location; mark
   unsupported claims UNSUPPORTED; label exploratory versus confirmatory;
   mark missing experiments TO-RUN. For `design` the ledger is prospective:
   every falsifiable claim maps to a planned artifact path, all marked
   TO-RUN, and the gate approves the mapping, not measured numbers. Gate:
   the human approves the ledger per `gate-protocol`.
3. Outline: rank 2-3 framings; freeze one against `outline-template` and
   the format's structure in `section-guide`. Freeze the one-sentence key
   insight at outline time, and fix the arc (problem, limits of current
   practice, insight, contributions, headline results) before drafting
   prose.
4. Drafting: write section by section in the venue's LaTeX template
   (fetched at intake), with word budgets. Every empirical sentence traces
   to a ledger entry or verified citation; mark the rest `[CITATION
   NEEDED]`. Put each mechanism's worked numerical example beside the prose
   that explains it.
5. Citation verification: file the report (`citation-report-template`).
   Per citation, check that the source exists (API lookup), that the fields
   belong to it, and that it supports the citing sentence. Retrieve in
   order: Semantic Scholar, OpenAlex, Crossref, arXiv API; record which
   source supplied each entry. Fix, downgrade, or cut.
6. Figure and table audit: every referenced figure and table exists;
   captions describe what is shown; prose numbers match artifacts.
7. Adversarial review: review the draft as a hostile reviewer per
   `reviewer-checklist`, write a punch list, revise, and repeat until the
   punch list clears. Then run the taste pass (`reviewer-checklist` pass
   5): the scenario stays concrete and practitioner-recognizable, the prose
   shows how each mechanism works, the one-sentence insight survives a cold
   read, and every omitted load-bearing detail (feedback model, failure
   model, measurement versus simulation, baseline tuning) carries a stated
   reason. Then apply the best-paper lens (`award-patterns` 6,
   `award-assessment`): the contradiction is sharp; experiments kill rival
   explanations; the evaluation is layered in the venue's currency; losses
   are reported honestly; threshold dimensions hold and the lead
   differentiators frame the paper.
8. Bundle and venue statements: assemble the reproducibility bundle (code
   and data pointers, seeds, logs, figure scripts; anonymized for
   double-blind). Compile the venue template and fix every error and
   warning that touches the submission. Write venue statements per
   `venue-standards`, only those the CFP requires. Gate: the human approves
   the final draft per `gate-protocol`.
9. Rebuttal and camera-ready (`rebut`; `rebuttal-playbook`): the input is
   the reviews as text, per reviewer the quoted concerns and scores, in any
   readable layout. Answer every concern, with depth set by decision
   leverage; run feasible requested experiments in-window and name the new
   artifacts; correct factual errors first with exact pointers; stay in
   multi-turn discussion. Close with an AC-facing summary table plus the
   response-to-reviewer mapping (`rebuttal-mapping-template`), or, for R&R
   venues, a tracked-changes revision plus a response letter. After
   acceptance: de-anonymize, add acknowledgments and artifact links,
   re-check camera-ready limits against the current CFP, and re-verify new
   citations.

## Output contract

- `design`: research plan per `design-plan-template` (scenario sketch,
  contradiction, falsifiable claims, worked example, experiment plan, award
  assessment: blocking weaknesses, lead differentiators, evidence gaps) plus
  a prospective evidence ledger (claim-to-artifact mapping, all TO-RUN). No
  results prose.
- `build`: complete draft in the venue's template within its limits,
  double-blind; venue brief; evidence ledger; citation verification report;
  reviewer punch list with resolutions; reproducibility bundle manifest;
  explicit AI-assistance disclosure.
- `refactor`: retargeted draft plus a change map (kept, cut, and rewritten
  sections, each with its reason).
- `rebut`: rebuttal draft or revision letter plus the response-to-reviewer
  mapping.

## Operating rules

1. Write only what artifacts and verified citations support. Mark the rest
   `[CITATION NEEDED]` or cut it.
2. Fetch every BibTeX entry via API.
3. Trace every empirical claim to an evidence-ledger entry; ground every
   novelty claim in cited retrieved literature.
4. Take venue facts from the current official CFP, never from memory.
   Record the cycle year and source URLs.
5. Describe in results sections what ran, not what was planned. Report
   failed or narrowed experiments as such.
6. Keep load-bearing claims and key numbers in the main body; reviewers are
   not required to read appendices.
7. LLM self-review improves prose; it never certifies integrity. The
   integrity gate is the human-approved evidence ledger plus provenance.
8. Back adjectives like "significant", "best", or "SOTA" with statistical or
   evidential backing.
9. Follow the venue's style files exactly. If no venue is specified, default
   to APA 7.
10. Default prose: active voice, precise claims, short paragraphs.
11. Keep run state current: working notes in `<run-dir>/RUN.md`, coarse
    events in `<run-dir>/TRACE.jsonl`; record every gate decision verbatim
    in the trace.
