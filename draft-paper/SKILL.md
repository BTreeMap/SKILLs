---
name: draft-paper
description: >-
  Draft a conference, workshop, journal, survey, or demo paper from a rough
  idea, partial results, or full results. Use when the user wants to turn
  research into a submittable draft, refactor it for a new venue or format,
  or rebut reviews.
license: MIT
compatibility: >-
  Network access is needed for CFP verification and literature retrieval;
  without it, venue facts ship flagged as unverified.
metadata:
  argument-hint: "[design|build|refactor|rebut] [short|full|workshop|journal|survey|demo]"
---

# Draft Paper

Turns research at any stage into a submittable paper draft. The **verb**
(what to do) and the **format** (what to produce) route each run. The
pipeline is one continuous sequence; verbs select entry and exit points
along it.

## Registry

| Name | Path |
| --- | --- |
| `venue-standards` | `references/venue-standards.md` |
| `section-guide` | `references/section-guide.md` |
| `award-patterns` | `references/award-patterns.md` |
| `reviewer-checklist` | `references/reviewer-checklist.md` |
| `rebuttal-playbook` | `references/rebuttal-playbook.md` |
| `evidence-ledger-template` | `references/evidence-ledger-template.md` |
| `outline-template` | `references/outline-template.md` |
| `award-assessment` | `references/award-assessment.md` |
| `run-template` | `references/run-template.md` |
| `trace-schema` | `references/trace-schema.md` |
| `gate-protocol` | `references/gate-protocol.md` |
| `design-plan-template` | `references/design-plan-template.md` |
| `venue-brief-template` | `references/venue-brief-template.md` |
| `citation-report-template` | `references/citation-report-template.md` |
| `rebuttal-mapping-template` | `references/rebuttal-mapping-template.md` |
| `help` | `references/help.md` |

Each file owns one concern: `venue-standards` owns venue verification;
`section-guide` owns section structure; `award-patterns` owns empirical
patterns; `reviewer-checklist` owns review criteria; `rebuttal-playbook`
owns post-submission response; `run-template` owns the scratchpad;
`trace-schema` owns the event log; `gate-protocol` owns the approval
handshake; `design-plan-template` owns the stage-1 plan;
`venue-brief-template` owns venue facts; `citation-report-template` owns
citation verification; `rebuttal-mapping-template` owns the review response
map; `help` prints the dispatch card. This file owns dispatch, the pipeline,
contracts, and rules.

## Scripts

Trace verification ships as a bundled uv workspace member under `scripts/`,
following the repository's script conventions: one console entry point,
`btm-draft-paper`, with reading, the event cap, and the failure type reused
from the `btm-corekit` kernel.

<commands>
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-draft-paper"
$R trace verify <run-dir>
</commands>

## Verbs

| Verb | Starts from | Runs stages | Delivers |
| --- | --- | --- | --- |
| `design` | spark or shaped idea | 1-2 | positioned research plan |
| `build` | shaped idea, partial or full results | 2-8 | complete draft |
| `refactor` | existing draft | 3-8, abbreviated | draft retargeted to a new format or venue |
| `rebut` | reviews received | 9 | rebuttal or revision letter |
| `help` | any | none (one-shot) | dispatch reference card |

Verbs reuse the family vocabulary: `design` plans the research before it
runs (cf. `/advisor design`), `build` produces the artifact (cf.
`/aesthete build`), `refactor` restructures an existing draft under new
constraints with its claims preserved (cf. `/ponytail refactor`). `rebut`
has no family counterpart; it answers reviews. `help` prints the dispatch
card and changes nothing.

Dispatch by explicit verb, then by request shape (rough idea: `design`;
results: `build`; reviews: `rebut`), then by the default verb `build`.

## Input states

- **spark**: a few sentences of idea. `design` positions it; nothing is
  written as fact.
- **shaped**: hypothesis plus literature context or early evidence. `design`
  sharpens the plan; `build` starts a partial ledger.
- **partial results**: some experiments done. `build` ledgers what exists,
  marks the rest TO-RUN, and states only what ran.
- **full results**: complete artifact set. `build` runs the full pipeline.
- **existing draft**: for `refactor` only. Re-outline against the new format
  and venue checklist; keep unchanged sections.

If the state is ambiguous, ask exactly one question.

## Formats

| Format | Typical shape | Structure |
| --- | --- | --- |
| `short` | 6-page idea paper (HotNets/HotOS/HotStorage style) | `section-guide`, short track |
| `full` | conference full paper; page budget from the CFP | `section-guide`, full track |
| `workshop` | 4-6 pages, preliminary work | `section-guide`, workshop |
| `journal` | extended, no hard cap, revision rounds | `section-guide`, journal |
| `survey` | taxonomy and gaps, no novel experiments | `section-guide`, survey |
| `demo` | 2-4 pages plus a live artifact | `section-guide`, demo |

If the format is unknown, ask exactly one question. Defaults: `full` for
results, `short` for a spark with a strong contradiction.

## Pipeline

0. **Intake.** Detect state and verb; confirm format. Record target venue
   (if unknown, ask), backbone model version (pin it; reliability
   assumptions do not transfer across models), artifact paths. Create the
   run directory: `<run-dir>/RUN.md` from `run-template`, and
   `<run-dir>/TRACE.jsonl` seeded with a `run-started` event (see
   `trace-schema`). **Study the current CFP** per `venue-standards`; record
   cycle year and source URLs in the venue brief (`venue-brief-template`),
   and fetch the venue's LaTeX template now.
1. **Positioning.** (`design`; `build` validates it for shaped inputs.)
   Literature sweep via retrieval APIs; gap analysis; novelty argument from
   retrieved full text; falsifiable claims; pre-registration-style
   experiment plan. Write the design plan (`design-plan-template`): a
   concrete scenario sketch that passes the practitioner-recognition test,
   the contradiction framing (`award-patterns` 1), a worked numerical
   example of the core mechanism, and the award assessment
   (`award-assessment`). **Gate:** human approves the plan per
   `gate-protocol`.
2. **Evidence.** Build the evidence ledger (`evidence-ledger-template`):
   every quantitative claim maps to an artifact file and location;
   unsupported claims marked UNSUPPORTED; exploratory vs confirmatory
   labeled; missing experiments marked TO-RUN. For `design` the ledger is
   prospective: every falsifiable claim maps to a planned artifact path, all
   marked TO-RUN; the gate approves the mapping, not measured numbers.
   **Gate:** human approves the ledger per `gate-protocol`.
3. **Outline.** Rank 2-3 framings; freeze one against `outline-template` and
   the format's structure in `section-guide`.
4. **Drafting.** Section by section in the venue's LaTeX template (fetched
   at intake), with word budgets. Every empirical sentence traces to a
   ledger entry or verified citation; the rest marked `[CITATION NEEDED]`.
   Each mechanism gets its worked numerical example beside the prose that
   explains it.
5. **Citation verification.** File the report (`citation-report-template`):
   per citation, the source exists (API lookup), the fields belong to it,
   and it supports the citing sentence. Retrieval fallback in order:
   Semantic Scholar, OpenAlex, Crossref, arXiv API; record which source
   supplied each entry. Fix, downgrade, or cut.
6. **Figure and table audit.** Every referenced figure/table exists;
   captions describe what is shown; prose numbers match artifacts.
7. **Adversarial review.** `reviewer-checklist` as hostile reviewer; punch
   list, revise, repeat once. Then the taste pass (`reviewer-checklist` pass
   5): the scenario stays concrete and practitioner-recognizable, the prose
   shows how each mechanism works, and no load-bearing detail (feedback
   model, failure model, measurement vs simulation, baseline tuning) is
   omitted without a stated reason. Best-paper lens (`award-patterns` 6,
   `award-assessment`): contradiction sharp; experiments kill rival
   explanations; evaluation layered in the venue's currency; losses honest;
   threshold dimensions hold and the lead differentiators frame the paper.
8. **Bundle and venue statements.** Reproducibility bundle (code/data
   pointers, seeds, logs, figure scripts; anonymized for double-blind).
   Compile the venue template; fix every error and warning that touches the
   submission. Venue statements per `venue-standards` (only what the CFP
   requires). **Gate:** human approves the final draft per `gate-protocol`.
9. **Rebuttal and camera-ready** (`rebut` verb; `rebuttal-playbook`). Input:
   the reviews as text, per reviewer quoted concerns and scores in any
   readable layout. Answer every concern, depth by decision leverage; run
   feasible requested experiments in-window and name new artifacts; correct
   factual errors first with exact pointers; multi-turn discussion; close
   with an AC-facing summary table plus the response-to-reviewer mapping
   (`rebuttal-mapping-template`), or a tracked-changes revision plus
   response letter for R&R venues. After acceptance: de-anonymize, add
   acknowledgments and artifact links, re-check camera-ready limits against
   the current CFP, re-verify new citations.

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
- `refactor`: retargeted draft plus a change map (kept / cut / rewritten
  sections and why).
- `rebut`: rebuttal draft or revision letter plus the response-to-reviewer
  mapping.

## Operating rules

1. Write only what artifacts and verified citations support. Mark the rest
   `[CITATION NEEDED]` or cut it.
2. Fetch every BibTeX entry via API.
3. Trace every empirical claim to an evidence-ledger entry; ground every
   novelty claim in cited retrieved literature.
4. Venue facts come from the current official CFP, never from memory. Record
   cycle year and source URLs.
5. Results sections describe what ran, not what was planned. Failed or
   narrowed experiments are reported as such.
6. Load-bearing claims and key numbers live in the main body. Reviewers are
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
