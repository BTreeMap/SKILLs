---
name: reframe
description: >-
  Turns a design or planning discussion into a testable direction judgment:
  a sharp thesis, the constraint actually binding, the target worth aiming
  at, what to stop doing, three routes costed from conservative through
  staged to clean, and the evidence that would prove the judgment wrong. Use
  when the user asks to challenge a conservative design, think bigger,
  define a greenfield target, escape incrementalism, reconsider legacy
  constraints, or establish big-picture direction, and during product,
  architecture, or planning discussions when compatibility fear, refactor
  cost, local details, or the current implementation are prematurely
  deciding the target model.
license: MIT
metadata:
  argument-hint: "[topic or decision]"
---

# Reframe

## Purpose

Open the decision frame before implementation gravity closes it. Choose the right decision horizon, system boundary, and target model.

Strategic altitude means big-picture judgment plus conceptual compression: prefer fewer concepts, clearer ownership, longer-lived boundaries, higher leverage. A larger diff alone is not a better strategy.

## Doctrine

<system_directives>
  <principles>
    <rule>Bold hypothesis, careful verification: open the frame, make the call, then make it falsifiable before execution commitment.</rule>
    <rule>Treat the thesis as a high-leverage hypothesis to test.</rule>
    <rule>Separate the right target from the path used to reach it.</rule>
    <rule>Price compatibility, migration, and refactor cost before they choose the target unpriced.</rule>
    <rule>Prefer conceptual deletion and boundary repair over additive architecture.</rule>
    <rule>Calibrate confidence from evidence.</rule>
    <rule>Keep irreversible commitments behind the first discriminating proof point.</rule>
  </principles>
</system_directives>

## Trigger Gate

Invoke on explicit cues, including:

- "Think bigger," "raise the altitude," "step back," or "give me the big-picture call."
- "Too incremental," "too safe," "too conservative," or "stop optimizing locally."
- "Greenfield this," "ignore the legacy for a moment," or "what would we build today?"
- "Do not let compatibility or refactor difficulty dictate the direction."

Invoke proactively only when at least one symptom exists:

- A local patch is chosen before the target model is stated.
- Compatibility is preserved without a named contract or stakeholder.
- The current package, document, process, or partial implementation is treated as immutable.
- Migration size is used to reject a direction before its value is assessed.
- Many small concepts obscure one lifecycle, owner, or product promise.
- Proposed options differ in mechanics but preserve the same questionable frame.

A small proposal alone is not a trigger. Small can be the correct answer when the boundary, target, and evidence support it.

## Required Inputs

Derive from supplied material before asking questions:

- Decision to make.
- Outcome and useful time horizon.
- Current proposal or inherited model.
- Known contracts and stakeholders.
- Claimed constraints and supporting evidence.

If a repository or document set is available:

1. Search for public contracts, persisted schemas, integrations, callers, tests, migration code, and ownership boundaries.
2. Read representative definitions and call sites; avoid exhaustive archaeology before forming the thesis.
3. Inspect version history only when intent or compatibility status could change the decision.
4. Label every unsupported claim as an assumption.

If the outcome, horizon, boundary, or owner is missing, ask only when the answer could change the target model. Otherwise, state the assumption and lower confidence.

## Constraint Classification

Classify each inherited constraint before using it:

| Class | Evidence | Treatment |
| --- | --- | --- |
| Contract | Public API, persisted data, documented integration, user promise, compliance rule, deployment limit, explicit instruction | Preserve, migrate deliberately, or renegotiate openly |
| Delivery constraint | Deadline, budget, staffing, rollout window, operational capacity | Price in the path; keep it out of the target architecture |
| Migration cost | Internal callers, relearning, diff size, temporary dual operation | Estimate and stage if justified; call it compatibility only with evidence |
| Inertia | Stale name, old package layout, partial implementation, document shape, "already built" | Remove from target reasoning |
| Unknown | Asserted constraint without inspectable evidence | Name the assumption; seek the cheapest deciding evidence |

Internal usage creates work; a contract needs evidence.

## Frame-Opening Moves

Select the smallest set that exposes the hidden decision. Use at least one; name it in the output.

| Move | Question | Guardrail |
| --- | --- | --- |
| End-state backcasting | If this were excellent at the chosen horizon, what would be true? | Backcast to the present and keep the architecture grounded |
| Zero-legacy thought experiment | With no old callers or names, what model would we choose? | Restore only constraints proven real |
| Kill the wrong concept | Which object, phase, section, or service encodes the wrong model? | Delete the concept, label and all |
| Ten-times stress | Which plausible 10x axis makes the model fail first? | Choose one relevant axis and scale only that axis |
| Constraint inversion | If this constraint vanished, what would change? | Decide whether removal cost is worth paying |
| Non-negotiable principles | Which two to four rules must the target never violate? | Use principles to decide |
| Boundary reset | Is responsibility split at the wrong system, lifecycle, or ownership boundary? | Move boundaries only when ownership becomes clearer |
| Tasteful deletion | What can stop existing without reducing the intended outcome? | Name the lost behavior and affected stakeholder |

## Workflow

### 1. Reframe the decision

State the real choice at the highest useful level. Define outcome, horizon, system boundary, and decision owner. Reject vague goals such as "cleaner" or "more scalable."

If missing context could change the target, ask a focused question. If it cannot, continue with an explicit assumption.

### 2. Establish the evidence baseline

Separate observed facts, explicit instructions, and assumptions. Record missing evidence only when it can change the decision.

### 3. Diagnose the inherited frame

Name the constraint currently controlling the proposal. Classify it using the constraint table. State who or what requires it. Grant contract status only when evidence names one.

### 4. Open the frame

Apply one or more frame-opening moves. Explain the newly visible option, boundary, deletion, or principle. The result must simplify the model or increase durable leverage.

### 5. Form the clean target

Describe the end-state independently of migration:

- Core model and system boundary.
- Lifecycle owner and source of truth.
- Two to four non-negotiable principles.
- What survives.
- Kill list: what to delete, merge, split, rename, reframe, or rebuild.

Every kill-list item must identify the wrong assumption or duplicate responsibility it removes.

### 6. Name what not to do

Identify safe-looking actions that block the target:

- Local optimizations that fix symptoms while preserving the wrong boundary.
- Permanent shims or dual models without a named contract and retirement condition.
- Detail work that does not reduce uncertainty or advance the target.

Tie each warning to the target or kill-list item it would contradict.

### 7. Compare three paths

Use the canonical options:

- **Conservative path**: preserve the inherited model; minimize immediate disruption.
- **Clean target**: move directly to the preferred end-state.
- **Staged clean path**: preserve the same clean target; sequence reversible steps and retire temporary bridges explicitly.

Compare target integrity, immediate price, permanent complexity, contract risk, and time to evidence. Recommend one. Choose Staged only when it preserves the clean target and has explicit retirement. If a path is incoherent, mark it non-viable.

### 8. Make the call

Lead with a one-to-three-sentence thesis. State material tradeoffs without weakening the recommendation. Assign confidence:

- **High**: decisive contracts and representative evidence inspected; no major unresolved assumption.
- **Medium**: direction supported; one or more material assumptions remain testable.
- **Low**: thesis mainly opens the frame; decisive evidence is absent or contradictory.

### 9. Design the verification path

Specify:

- First proof point: cheapest artifact or observation that distinguishes this thesis from alternatives.
- Expected signal: observable result supporting the thesis.
- Falsifier: evidence that forces rejection or material revision.
- Deferred commitment: irreversible choice not to make before the signal arrives.

Make the proof point test the target model, contract assumption, boundary, or payoff; showing that code can be written is not enough.

### 10. Close the payoff ledger

For each major bold take or kill-list item, record:

- Price paid now.
- Specific pain removed or capability unlocked.
- Moment or signal when payoff appears.
- Stakeholder receiving the payoff.

Include only rows that justify the direction to someone paying for it. Reject rows based solely on "cleaner," "simpler," "more maintainable," or similar generic claims.

## Output Contract

Produce one strategic direction judgment in the user's language, using the template in this file. Keep its eleven sections in template order, Thesis first through Payoff Ledger last.

Output rules:

- Lead with the call; methodology and caveats follow.
- Keep target model separate from migration path.
- Give every compatibility mechanism a named contract, owner, and retirement condition.
- Use code-level detail only when it changes the direction or verifies a claim.
- Tie every ledger row to a bold take or kill-list item.
- End with the ledger; omit a second summary.

## Handoff Boundaries

Use another procedure when the primary decision is:

- Whether the idea deserves investment at all: do, kill, or defer.
- Detailed module boundaries, abstraction depth, or implementation-quality review.
- Execution planning after the target is accepted: migration sequencing, rollout, observability, and rollback.
- Writing the final product requirements document.

After the target is accepted, route it to an available feasibility or landing procedure. If none exists, state the unresolved landing questions.

## Gotchas

- Optimize the model; diff size is a price.
- Preserve named public and data contracts.
- Classify internal migration cost as migration cost.
- Keep temporary bridge design out of the clean target.
- Give every bridge an owner, removal trigger, and deadline or measurable gate.
- Give every bold take a falsifier; testability matters more than provocation.
- Make the proof point test the direction.
- Give the three option rows distinct tradeoffs.
- Tie each kill-list removal to the bad assumption it removes.
- Tie the payoff ledger to concrete outcomes.

## Validation

<validation_checklist>
  <directive>Silently verify before output.</directive>
  <item>Trigger gate satisfied by a real frame problem.</item>
  <item>Decision, outcome, horizon, and boundary stated.</item>
  <item>Facts, instructions, and assumptions separated.</item>
  <item>Each inherited constraint classified and evidenced.</item>
  <item>At least one frame-opening move applied and named.</item>
  <item>Clean target simplifies concepts or increases durable leverage.</item>
  <item>Target design and migration path remain separate.</item>
  <item>Kill list explains the wrong model each removal eliminates.</item>
  <item>Warnings identify actions that would preserve the wrong model.</item>
  <item>All three canonical paths compared or explicitly marked non-viable.</item>
  <item>Recommendation and confidence are explicit.</item>
  <item>Proof point distinguishes the thesis from alternatives.</item>
  <item>Falsifier could overturn the thesis.</item>
  <item>Every payoff row names price, specific payoff, visibility signal, and beneficiary.</item>
  <item>No generic benefit, default shim, fake certainty, or performative bigness remains.</item>
</validation_checklist>

## Output Template

Replace every `{{...}}` field. Remove all instructional placeholders before output. Preserve the section order and table structure.

<output_template>
# Strategic Direction: {{topic}}

## Thesis

{{Sharp, high-leverage hypothesis in one to three sentences. State the target and decisive tradeoff without claiming certainty.}}

## Confidence

- **Level**: {{high / medium / low}}
- **Evidence basis**: {{decisive evidence already inspected}}
- **Why not certain**: {{material missing evidence or assumption; write “none material” only when justified}}

## The Trap

- **Inherited constraint**: {{compatibility / delivery limit / migration cost / inertia / unknown}}
- **Classification**: {{contract / delivery constraint / migration cost / inertia / unknown}}
- **Who or what requires it**: {{named stakeholder, contract, artifact, or “not evidenced”}}
- **Judgment**: {{preserve / migrate / renegotiate / discard / verify}}

## Target Direction

- **Target model**: {{clean end-state independent of migration}}
- **System boundary**: {{where responsibility begins and ends}}
- **Lifecycle owner / source of truth**: {{one accountable owner or canonical artifact}}
- **Non-negotiable principles**:
  - {{principle one}}
  - {{principle two}}
- **What survives**: {{valuable contract, capability, or concept retained}}

## Frame-Opening Move

- **Move used**: {{end-state backcasting / zero-legacy thought experiment / kill the wrong concept / ten-times stress / constraint inversion / non-negotiable principles / boundary reset / tasteful deletion}}
- **What it reveals**: {{new option, boundary, deletion, or principle hidden by the inherited frame}}

## Bold Takes / Kill List

| Action | Target | Wrong model removed | Material tradeoff |
| --- | --- | --- | --- |
| {{delete / merge / split / rename / reframe / rebuild}} | {{specific concept, flow, phase, section, or abstraction}} | {{bad assumption or duplicate responsibility}} | {{real cost or capability lost}} |

## Options

| Option | Target integrity | Price now | Permanent complexity | Contract risk | Time to evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Conservative path | {{what remains compromised or protected}} | {{immediate cost}} | {{debt retained}} | {{named risk}} | {{duration or milestone}} | {{reject / use only if... / recommend}} |
| Clean target | {{degree of end-state fidelity}} | {{migration, disruption, or relearning}} | {{residual complexity}} | {{named risk}} | {{duration or milestone}} | {{reject / recommend}} |
| Staged clean path | {{same target, sequence only}} | {{sequencing and temporary bridge cost}} | {{retirement-dependent debt}} | {{named risk}} | {{first deciding milestone}} | {{fallback / recommend / non-viable}} |

## What Not To Do

- {{Local optimization, permanent shim, partial patch, or detail trap to avoid.}}
- {{Safe-looking action that preserves the wrong model.}}

## First Proof Point

- **Artifact or observation**: {{smallest discriminating test, trace, contract map, prototype, migration sample, interview, or decision record}}
- **Expected signal**: {{observable result supporting the thesis}}
- **Decision unlocked**: {{choice the signal permits}}
- **Deferred commitment**: {{irreversible choice withheld until evidence arrives}}

## Falsifier

{{Specific evidence that would reject or materially revise the thesis, plus the alternative it would favor.}}

## Payoff Ledger

| Move | Price paid now | Specific pain removed or capability unlocked | Beneficiary | When payoff becomes visible |
| --- | --- | --- | --- | --- |
| {{bold take or kill-list action}} | {{migration, disruption, relearning, or opportunity cost}} | {{concrete pain or unlock; no generic quality adjective}} | {{user, operator, team, business, or system owner}} | {{observable event, threshold, or milestone}} |
</output_template>
