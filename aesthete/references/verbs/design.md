# Verb: design

Takes request for surface; returns committed direction and composition plan,
decision document someone else could build from. Writes no implementation
code: snippet pinning token or motion curve is fine; component belongs to
`write`.

## Procedure

1. **Name primary goal.** One sentence: single action or understanding this
   surface optimizes. Everything competing with it is secondary. Surface
   with two primary goals is two surfaces; saying so is valid outcome.
2. **Map user's path.** Write shortest honest sequence from arrival to goal;
   count its steps, decisions, fields, waits: friction budget. Each item:
   state reason it exists or mark it for removal.
3. **Choose foundation**: repository's existing component library, official
   design system, or hand-composed system. Repository already uses one: that
   is the choice; otherwise return to spine and load `systems`.
4. **Set token spine** before composing, once for whole surface: type scale
   and pairing, spacing scale, radius scale, one accent, neutral family,
   motion curve family, elevation ladder, icon family and weight. Load craft
   owners from spine for any scale read does not settle.
5. **Compose sequence.** Marketing surface: plan section order, each section
   distinct layout family and job. Product surface: plan navigation model,
   density per region, primary, secondary, tertiary action placement. Every
   adjacent pair differs structurally; combine sections sharing job. Specify
   each region's mobile behavior while planning it.
6. **Decide accessibility posture**, compose within it: target contrast
   level, target size minimum, keyboard model, reduced-motion degradation.
7. **Write kill list.** Name what design deliberately excludes and why,
   including patterns brief invited that you decline, and what replaces
   each.
8. **Identify risks.** Name two or three decisions most likely wrong,
   evidence that would falsify each, fallback.

Commit to one direction. Fork exists: name it, pick side, state one question
whose answer would flip it.

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
  <item>Primary goal is one sentence; surface optimizes for it.</item>
  <item>Friction budget counted, itemized, reduced where possible.</item>
  <item>Foundation choice names repository's existing stack or stated reason to depart from it.</item>
  <item>Every token scale fixed once, with rule, before composition.</item>
  <item>Adjacent sections or regions differ structurally, carry distinct jobs.</item>
  <item>Kill list non-empty, names replacements.</item>
  <item>Mobile behavior and accessibility posture decided.</item>
  <item>Exactly one direction committed to.</item>
</checklist>
