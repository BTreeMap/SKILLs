# Verb: design

Produce a committed design direction and a composition plan before any code
exists. The deliverable is a decision document someone else could build
from.

## Preconditions

The design read and the three dials are already stated. If either is
missing, produce them first; everything below depends on them.

## Procedure

1. **Name the primary goal.** One sentence: the single action or
   understanding this surface optimizes. Everything competing with it is
   secondary by definition. A surface with two primary goals is two
   surfaces, and saying so is a valid design outcome.

2. **Map the user's path.** Write the shortest honest sequence from arrival
   to goal. Count the steps, decisions, fields, and waits. This count is the
   friction budget and it appears in the deliverable. For each item, either
   state the reason it exists or mark it for removal.

3. **Choose the foundation.** Decide between an official design system, the
   repository's existing component library, and a hand-composed system.
   Prefer, in order: what the repository already uses; an official system
   when the domain expects one; a hand-composed system only when the brand
   expression is itself the product. Return to the spine and load
   `systems` when this decision is live.

4. **Set the token spine.** Fix the scales before composing: type scale and
   pairing, spacing scale, radius scale, one accent, neutral family, motion
   curve family, elevation ladder, icon family and weight. These are
   decided once for the whole surface. Load the relevant craft references
   from the spine for any scale that is not obvious from the read.

5. **Compose the sequence.** For a marketing surface, plan the section
   order, assigning each section a distinct layout family and a job. For a
   product surface, plan the navigation model, the information density per
   region, and the primary/secondary/tertiary action placement. Every
   adjacent pair must differ structurally.

6. **Write the kill list.** Name what this design deliberately does not
   include and why. Include patterns the brief invited that you are
   declining, and say what replaces them.

7. **Identify the risks.** Name the two or three decisions most likely to be
   wrong, what evidence would falsify each, and what the fallback is.

## Deliverable

<design-deliverable>
## Design read
{one line}

## Dials
VARIANCE {n}: {reason from the read}
MOTION {n}: {reason}
DENSITY {n}: {reason}

## Primary goal
{one sentence}

## Friction budget
{n} steps to goal: {step} > {step} > {step}
Removed: {what was cut and why}

## Foundation
{system or stack}, because {reason}

## Token spine
Type: {display / body / mono, with scale}
Space: {scale}
Radius: {scale and the rule}
Accent: {one color and its role}
Neutrals: {family}
Motion: {curve family and duration band}
Icons: {family and weight}

## Composition
{ordered sections or regions, each with job and layout family}

## Kill list
{pattern}: declined because {reason}; {replacement} instead

## Risks
{decision}: wrong if {falsifier}; fallback is {alternative}
</design-deliverable>

## Rules

* Commit to one direction. If a genuine fork exists, name the fork, pick a side, and state the one question whose
  answer would flip it.
* Give every section and region a distinct job. Combine sections that share
  a job.
* Specify mobile behavior for each region while planning it.
* Decide accessibility posture here: target contrast level, target size
  minimum, keyboard model, and reduced-motion degradation. Use these
  constraints while composing.
* Keep implementation code out of this verb. A snippet pinning a token or a
  motion curve is fine; a component belongs to build.

## Completion checks

<validation-checklist>
  <item>Primary goal is one sentence and the surface optimizes for it.</item>
  <item>Friction budget is counted, itemized, and reduced where possible.</item>
  <item>Foundation choice names the repository's existing stack or a stated reason to depart from it.</item>
  <item>Every token scale is fixed once, with a rule, before composition.</item>
  <item>Adjacent sections or regions differ structurally and carry distinct jobs.</item>
  <item>Kill list is non-empty and names replacements.</item>
  <item>Mobile behavior and accessibility posture are decided.</item>
  <item>Exactly one direction is committed to.</item>
</validation-checklist>
