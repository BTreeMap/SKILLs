# Verb: design

Takes a request for a surface; returns a committed direction and composition
plan, a decision document someone else could build from. Writes no
implementation code: a snippet pinning a token or a motion curve is fine; a
component belongs to `build`.

## Procedure

1. **Name the primary goal.** One sentence: the single action or
   understanding this surface optimizes. Everything competing with it is
   secondary. A surface with two primary goals is two surfaces, and saying
   so is a valid outcome.
2. **Map the user's path.** Write the shortest honest sequence from arrival
   to goal and count its steps, decisions, fields, and waits: the friction
   budget. For each item, state the reason it exists or mark it for removal.
3. **Choose the foundation**: the repository's existing component library,
   an official design system, or a hand-composed system. If the repository
   already uses one, that is the choice; otherwise return to the spine and
   load `systems`.
4. **Set the token spine** before composing, once for the whole surface:
   type scale and pairing, spacing scale, radius scale, one accent, neutral
   family, motion curve family, elevation ladder, icon family and weight.
   Load the craft owners from the spine for any scale the read does not
   settle.
5. **Compose the sequence.** On a marketing surface, plan the section order,
   giving each section a distinct layout family and job. On a product
   surface, plan the navigation model, the density per region, and primary,
   secondary, and tertiary action placement. Every adjacent pair differs
   structurally; combine sections that share a job. Specify each region's
   mobile behavior while planning it.
6. **Decide the accessibility posture** and compose within it: target
   contrast level, target size minimum, keyboard model, reduced-motion
   degradation.
7. **Write the kill list.** Name what the design deliberately excludes and
   why, including patterns the brief invited that you decline, and what
   replaces each.
8. **Identify the risks.** Name the two or three decisions most likely to be
   wrong, the evidence that would falsify each, and the fallback.

Commit to one direction. If a fork exists, name it, pick a side, and state
the one question whose answer would flip it.

## Deliverable

<template for="design">
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
</template>

## Completion checks

<checklist>
  <item>Primary goal is one sentence and the surface optimizes for it.</item>
  <item>Friction budget is counted, itemized, and reduced where possible.</item>
  <item>Foundation choice names the repository's existing stack or a stated reason to depart from it.</item>
  <item>Every token scale is fixed once, with a rule, before composition.</item>
  <item>Adjacent sections or regions differ structurally and carry distinct jobs.</item>
  <item>Kill list is non-empty and names replacements.</item>
  <item>Mobile behavior and accessibility posture are decided.</item>
  <item>Exactly one direction is committed to.</item>
</checklist>
