---
name: reframe
description: >-
  Turns design or planning discussion into testable direction judgment:
  thesis, binding constraint, target worth aiming at, what to stop doing,
  three costed routes from conservative to clean, evidence that would prove
  it wrong. Use when asked to think bigger, escape incrementalism,
  reconsider legacy constraints, or set direction, or when compatibility
  fear or refactor cost decides target too early.
license: MIT
metadata:
  argument-hint: "[topic or decision]"
---

# Reframe

Turn design or planning discussion into one strategic direction judgment.
Define decision horizon, system boundary, target model before choosing
implementation. Treat thesis as high-leverage hypothesis: open frame, make
the call, then make it falsifiable before any execution commitment.
Strategic altitude is conceptual compression: fewer concepts, clearer
ownership, longer-lived boundaries, higher leverage.

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

- Local patch chosen before target model is stated.
- Compatibility preserved without named contract or stakeholder.
- Current package, document, process, or partial implementation treated as
  immutable.
- Migration size used to reject direction before its value is assessed.
- Many small concepts obscure one lifecycle, owner, or product promise.
- Proposed options differ in mechanics but preserve same questionable frame.

Small proposal alone is not a trigger; it can be correct when boundary,
target, evidence support it.

## Inputs

Derive from supplied material before asking questions:

- Decision to make.
- Outcome and useful time horizon.
- Current proposal or inherited model.
- Known contracts and stakeholders.
- Claimed constraints and supporting evidence.

Input missing: ask one focused question only when answer could change target
model. Otherwise state assumption, lower confidence.

## Workflow

### 1. Reframe the decision

State real choice at highest useful level. Define outcome, horizon, system
boundary, decision owner. Reject vague goals such as "cleaner" or "more
scalable."

### 2. Establish the evidence baseline

Separate observed facts, explicit instructions, assumptions; label every
unsupported claim as assumption. Record missing evidence only when it can
change decision.

Repository or document set available:

1. Search for public contracts, persisted schemas, integrations, callers,
   tests, migration code, ownership boundaries.
2. Read representative definitions and call sites; avoid exhaustive
   archaeology before forming thesis.
3. Inspect version history only when intent or compatibility status could
   change decision.

### 3. Diagnose the inherited frame

Name constraint currently controlling proposal; state who or what requires
it. Classify it, and every other inherited constraint, by this table before
using it. Estimate compatibility, migration, refactor costs before letting
them determine target.

| Class | Evidence | Treatment |
| --- | --- | --- |
| Contract | Public API, persisted data, documented integration, user promise, compliance rule, deployment limit, explicit instruction | Preserve, migrate deliberately, or renegotiate openly |
| Delivery constraint | Deadline, budget, staffing, rollout window, operational capacity | Price in the path; keep it out of target architecture |
| Migration cost | Internal callers, relearning, diff size, temporary dual operation | Estimate and stage if justified; call it compatibility only with evidence |
| Inertia | Stale name, old package layout, partial implementation, document shape, "already built" | Remove from target reasoning |
| Unknown | Asserted constraint without inspectable evidence | Name assumption; seek cheapest deciding evidence |

Internal usage creates work; grant contract status only when evidence names
a contract.

### 4. Open the frame

Apply smallest set of these moves exposing hidden decision, at least one;
name each move in output. Explain newly visible option, boundary, deletion,
or principle.

| Move | Question | Guardrail |
| --- | --- | --- |
| End-state backcasting | If this were excellent at the chosen horizon, what would be true? | Backcast to present; keep architecture grounded |
| Zero-legacy thought experiment | With no old callers or names, what model would we choose? | Restore only constraints proven real |
| Kill the wrong concept | Which object, phase, section, or service encodes the wrong model? | Delete concept, label and all |
| Ten-times stress | Which plausible 10x axis makes the model fail first? | Choose one relevant axis, scale only that axis |
| Constraint inversion | If this constraint vanished, what would change? | Decide whether removal cost is worth paying |
| Non-negotiable principles | Which two to four rules must the target never violate? | Use principles to decide |
| Boundary reset | Is responsibility split at the wrong system, lifecycle, or ownership boundary? | Move boundaries only when ownership becomes clearer |
| Tasteful deletion | What can stop existing without reducing the intended outcome? | Name lost behavior and affected stakeholder |

### 5. Form the clean target

Describe end-state independently of migration; keep target separate from
path reaching it, in reasoning and output alike. Prefer conceptual deletion
and boundary repair over additive architecture. State:

- Core model and system boundary.
- Lifecycle owner and source of truth.
- Two to four non-negotiable principles.
- What survives.
- Kill list: what to delete, merge, split, rename, reframe, or rebuild.

### 6. Name what not to do

Identify safe-looking actions that block target:

- Local optimizations fixing symptoms while preserving wrong boundary.
- Permanent shims or dual models without named contract and retirement
  condition.
- Detail work that neither reduces uncertainty nor advances target.

### 7. Compare three paths

Use canonical options:

- **Conservative path**: preserve inherited model; minimize immediate
  disruption.
- **Clean target**: move directly to preferred end-state.
- **Staged clean path**: preserve same clean target; sequence reversible
  steps; give every temporary bridge owner, removal trigger, and deadline or
  measurable gate.

Compare target integrity, immediate price, permanent complexity, contract
risk, time to evidence; give three rows distinct tradeoffs. Path incoherent:
mark it non-viable. Recommend one; choose Staged only when it preserves
clean target and has explicit retirement. Give every compatibility mechanism
named contract, owner, retirement condition.

### 8. Make the call

State material tradeoffs without weakening recommendation. Assign confidence
from evidence:

- **High**: decisive contracts and representative evidence inspected; no
  major unresolved assumption.
- **Medium**: direction supported; one or more material assumptions remain
  testable.
- **Low**: thesis mainly opens frame; decisive evidence absent or
  contradictory.

### 9. Design the verification path

Specify First Proof Point fields, then Falsifier section:

- Artifact or observation: cheapest artifact or observation distinguishing
  this thesis from alternatives.
- Expected signal: observable result supporting thesis.
- Decision unlocked: choice signal permits.
- Deferred commitment: irreversible choice not to make before signal
  arrives.
- Falsifier: evidence forcing rejection or material revision, and
  alternative it would favor.

Proof point tests target model, contract assumption, boundary, or payoff;
showing code can be written is not enough. Keep every irreversible
commitment behind this proof point; give every bold take a falsifier.

### 10. Close the payoff ledger

For each major bold take or kill-list item, record one row; tie every row to
such an item:

- Price paid now.
- Specific pain removed or capability unlocked.
- Moment or signal when payoff appears.
- Stakeholder receiving payoff.

Reject rows based solely on "cleaner," "simpler," "more maintainable," or
similar generic claims.

## Output

Produce one strategic direction judgment in user's language from template
below. Replace every `{{...}}` field; remove every instructional
placeholder. Keep eleven sections in template order, Thesis first through
Payoff Ledger last; keep table structure.

- Lead with the call; methodology and caveats follow.
- Code-level detail only when it changes direction or verifies claim.
- End with ledger; omit second summary.

After target is accepted, route it to available feasibility or landing
procedure, or state unresolved landing questions.

```markdown
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
```

## Validation

- Trigger gate satisfied by real frame problem.
- Decision, outcome, horizon, boundary stated.
- Facts, instructions, assumptions separated.
- Each inherited constraint classified and evidenced.
- At least one frame-opening move applied and named.
- Clean target simplifies concepts or increases durable leverage.
- Target design and migration path stay separate.
- Kill list explains wrong model each removal eliminates.
- Warnings identify actions that would preserve wrong model.
- All three canonical paths compared or marked non-viable.
- Recommendation and confidence explicit.
- Proof point distinguishes thesis from alternatives.
- Falsifier could overturn thesis.
- Every payoff row names price, specific payoff, visibility signal,
  beneficiary.
- No generic benefit, default shim, fake certainty, or performative bigness
  remains.
