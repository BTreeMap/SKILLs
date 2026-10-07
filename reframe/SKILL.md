---
name: reframe
description: >-
  Turns a design or planning discussion into a testable direction judgment:
  a thesis, the binding constraint, the target worth aiming at, what to stop
  doing, three costed routes from conservative to clean, and the evidence
  that would prove it wrong. Use when asked to think bigger, escape
  incrementalism, reconsider legacy constraints, or set direction, or when
  compatibility fear or refactor cost is deciding the target too early.
license: MIT
metadata:
  argument-hint: "[topic or decision]"
---

# Reframe

Turn a design or planning discussion into one strategic direction judgment.
Define the decision horizon, system boundary, and target model before
choosing an implementation. Treat the thesis as a high-leverage hypothesis:
open the frame, make the call, then make it falsifiable before any execution
commitment. Strategic altitude is conceptual compression: fewer concepts,
clearer ownership, longer-lived boundaries, higher leverage.

## Redirects

- Whether to do, kill, or defer the idea: give the call plainly from the
  evidence at hand; reframe only what proceeds
- Module boundaries, abstraction depth, or implementation quality:
  `/pl-theorist` or `/ponytail`
- Migration sequencing, rollout, observability, and rollback: plan them as
  ordinary engineering work once the target is accepted
- Writing the product requirements document: write it from the accepted
  target in the team's own format

## Trigger Gate

Invoke on explicit cues, including:

- "Think bigger," "raise the altitude," "step back," or "give me the
  big-picture call."
- "Too incremental," "too safe," "too conservative," or "stop optimizing
  locally."
- "Greenfield this," "ignore the legacy for a moment," or "what would we
  build today?"
- "Do not let compatibility or refactor difficulty dictate the direction."

Invoke proactively only when at least one symptom exists:

- A local patch is chosen before the target model is stated.
- Compatibility is preserved without a named contract or stakeholder.
- The current package, document, process, or partial implementation is
  treated as immutable.
- Migration size is used to reject a direction before its value is assessed.
- Many small concepts obscure one lifecycle, owner, or product promise.
- Proposed options differ in mechanics but preserve the same questionable
  frame.

A small proposal alone is not a trigger; it can be correct when the
boundary, target, and evidence support it.

## Inputs

Derive these from supplied material before asking questions:

- Decision to make.
- Outcome and useful time horizon.
- Current proposal or inherited model.
- Known contracts and stakeholders.
- Claimed constraints and supporting evidence.

If an input is missing, ask one focused question only when the answer could
change the target model. Otherwise, state the assumption and lower
confidence.

## Workflow

### 1. Reframe the decision

State the real choice at the highest useful level. Define outcome, horizon,
system boundary, and decision owner. Reject vague goals such as "cleaner" or
"more scalable."

### 2. Establish the evidence baseline

Separate observed facts, explicit instructions, and assumptions; label every
unsupported claim as an assumption. Record missing evidence only when it can
change the decision.

If a repository or document set is available:

1. Search for public contracts, persisted schemas, integrations, callers,
   tests, migration code, and ownership boundaries.
2. Read representative definitions and call sites; avoid exhaustive
   archaeology before forming the thesis.
3. Inspect version history only when intent or compatibility status could
   change the decision.

### 3. Diagnose the inherited frame

Name the constraint currently controlling the proposal and state who or what
requires it. Classify it, and every other inherited constraint, by this
table before using it. Estimate compatibility, migration, and refactor costs
before letting them determine the target.

| Class | Evidence | Treatment |
| --- | --- | --- |
| Contract | Public API, persisted data, documented integration, user promise, compliance rule, deployment limit, explicit instruction | Preserve, migrate deliberately, or renegotiate openly |
| Delivery constraint | Deadline, budget, staffing, rollout window, operational capacity | Price in the path; keep it out of the target architecture |
| Migration cost | Internal callers, relearning, diff size, temporary dual operation | Estimate and stage if justified; call it compatibility only with evidence |
| Inertia | Stale name, old package layout, partial implementation, document shape, "already built" | Remove from target reasoning |
| Unknown | Asserted constraint without inspectable evidence | Name the assumption; seek the cheapest deciding evidence |

Internal usage creates work; grant contract status only when evidence names
a contract.

### 4. Open the frame

Apply the smallest set of these moves that exposes the hidden decision, at
least one, and name each move in the output. Explain the newly visible
option, boundary, deletion, or principle.

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

### 5. Form the clean target

Describe the end-state independently of migration, and keep the target
separate from the path that reaches it in reasoning and output alike. Prefer
conceptual deletion and boundary repair over additive architecture. State:

- Core model and system boundary.
- Lifecycle owner and source of truth.
- Two to four non-negotiable principles.
- What survives.
- Kill list: what to delete, merge, split, rename, reframe, or rebuild.

### 6. Name what not to do

Identify safe-looking actions that block the target:

- Local optimizations that fix symptoms while preserving the wrong boundary.
- Permanent shims or dual models without a named contract and retirement
  condition.
- Detail work that does not reduce uncertainty or advance the target.

### 7. Compare three paths

Use the canonical options:

- **Conservative path**: preserve the inherited model; minimize immediate
  disruption.
- **Clean target**: move directly to the preferred end-state.
- **Staged clean path**: preserve the same clean target; sequence reversible
  steps and give every temporary bridge an owner, a removal trigger, and a
  deadline or measurable gate.

Compare target integrity, immediate price, permanent complexity, contract
risk, and time to evidence, and give the three rows distinct tradeoffs. If a
path is incoherent, mark it non-viable. Recommend one; choose Staged only
when it preserves the clean target and has explicit retirement. Give every
compatibility mechanism a named contract, owner, and retirement condition.

### 8. Make the call

State material tradeoffs without weakening the recommendation. Assign
confidence from the evidence:

- **High**: decisive contracts and representative evidence inspected; no
  major unresolved assumption.
- **Medium**: direction supported; one or more material assumptions remain
  testable.
- **Low**: thesis mainly opens the frame; decisive evidence is absent or
  contradictory.

### 9. Design the verification path

Specify the First Proof Point fields, then the Falsifier section:

- Artifact or observation: cheapest artifact or observation that
  distinguishes this thesis from alternatives.
- Expected signal: observable result supporting the thesis.
- Decision unlocked: choice the signal permits.
- Deferred commitment: irreversible choice not to make before the signal
  arrives.
- Falsifier: evidence that forces rejection or material revision, and the
  alternative it would favor.

Make the proof point test the target model, contract assumption, boundary,
or payoff; showing that code can be written is not enough. Keep every
irreversible commitment behind this proof point, and give every bold take a
falsifier.

### 10. Close the payoff ledger

For each major bold take or kill-list item, record one row, and tie every
row to such an item:

- Price paid now.
- Specific pain removed or capability unlocked.
- Moment or signal when payoff appears.
- Stakeholder receiving the payoff.

Reject rows based solely on "cleaner," "simpler," "more maintainable," or
similar generic claims.

## Output

Produce one strategic direction judgment in the user's language from the
template below. Replace every `{{...}}` field and remove every instructional
placeholder. Keep the eleven sections in template order, Thesis first
through Payoff Ledger last, and keep the table structure.

- Lead with the call; methodology and caveats follow.
- Use code-level detail only when it changes the direction or verifies a
  claim.
- End with the ledger; omit a second summary.

After the target is accepted, route it to an available feasibility or
landing procedure, or state the unresolved landing questions.

<template for="output">
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
</template>

## Validation

<checklist>
  <item>Trigger gate satisfied by a real frame problem.</item>
  <item>Decision, outcome, horizon, and boundary stated.</item>
  <item>Facts, instructions, and assumptions separated.</item>
  <item>Each inherited constraint classified and evidenced.</item>
  <item>At least one frame-opening move applied and named.</item>
  <item>Clean target simplifies concepts or increases durable leverage.</item>
  <item>Target design and migration path remain separate.</item>
  <item>Kill list explains the wrong model each removal eliminates.</item>
  <item>Warnings identify actions that would preserve the wrong model.</item>
  <item>All three canonical paths compared or marked non-viable.</item>
  <item>Recommendation and confidence are explicit.</item>
  <item>Proof point distinguishes the thesis from alternatives.</item>
  <item>Falsifier could overturn the thesis.</item>
  <item>Every payoff row names price, specific payoff, visibility signal, and beneficiary.</item>
  <item>No generic benefit, default shim, fake certainty, or performative bigness remains.</item>
</checklist>
