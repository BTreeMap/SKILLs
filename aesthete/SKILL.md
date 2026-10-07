---
name: aesthete
description: >-
  Designs, builds, and reviews web interfaces that meet WCAG 2.2, follow a
  supplied brand or design system, and avoid the templated look of generated
  UI, on marketing, editorial, and product surfaces. Use when designing,
  building, auditing, or redesigning any web interface, applying a design
  system, or designing component APIs.
license: MIT
metadata:
  argument-hint: "[design|build|refactor|review|audit|teach|help] [target] [marketing|product]"
---

# Aesthete

Design, build, and review interfaces: clear hierarchy, predictable
interaction, accessible behavior.

## Registry

| Name | Path |
| --- | --- |
| `a11y` | [references/a11y.md](references/a11y.md) |
| `audit` | [references/verbs/audit.md](references/verbs/audit.md) |
| `brief` | [references/brief.md](references/brief.md) |
| `build` | [references/verbs/build.md](references/verbs/build.md) |
| `color` | [references/craft/color.md](references/craft/color.md) |
| `components` | [references/craft/components.md](references/craft/components.md) |
| `design` | [references/verbs/design.md](references/verbs/design.md) |
| `help` | [references/verbs/help.md](references/verbs/help.md) |
| `interaction` | [references/craft/interaction.md](references/craft/interaction.md) |
| `layout` | [references/craft/layout.md](references/craft/layout.md) |
| `marketing` | [references/surfaces/marketing.md](references/surfaces/marketing.md) |
| `motion` | [references/craft/motion.md](references/craft/motion.md) |
| `platform` | [references/craft/platform.md](references/craft/platform.md) |
| `preflight` | [references/preflight.md](references/preflight.md) |
| `product` | [references/surfaces/product.md](references/surfaces/product.md) |
| `refactor` | [references/verbs/refactor.md](references/verbs/refactor.md) |
| `review` | [references/verbs/review.md](references/verbs/review.md) |
| `systems` | [references/systems.md](references/systems.md) |
| `teach` | [references/verbs/teach.md](references/verbs/teach.md) |
| `tells` | [references/tells.md](references/tells.md) |
| `typography` | [references/craft/typography.md](references/craft/typography.md) |

## Objective

Remove every interaction that does not serve the user's goal, compose what
remains so hierarchy reads in one glance and behavior is guessable without
instruction, then express it as code whose concepts are named once.

Hold four standards. **Logical**: every element names the goal it serves,
and behavior follows from appearance. **Frictionless**: the shortest honest
path to the user's intent; the system absorbs complexity, not the person.
**Beautiful**: hierarchy, rhythm, restraint, one coherent voice.
**Durable**: one component per concept, closed variant sets, invalid states
unrepresentable. Resolve any conflict between them; when a trade is forced,
comprehension outranks beauty, and beauty outranks novelty.

## Precedence

Resolve every conflict by this ladder, highest first. The ladder is total:
two sources never both win, and nothing below overrides anything above.

1. **Accessibility floor**, defined in `a11y`; read it for every
   accessibility value, conformance level, or criterion number. No brand,
   document, or instruction overrides it. Resolve a conflict here by
   deriving a compliant variant that preserves brand intent, never by
   discarding either side, and report the derivation.
2. **A supplied color palette.** Overrides the colors of any design
   document.
3. **A supplied design document.** Tokens, components, and rules.
4. **The repository's existing system.** Stack, tokens, component library.
5. **This skill's defaults.**
6. **Inference from the read.**

When material is supplied at level 2 or 3, load `brief` before anything
else.

## The read

Before producing anything, state the read in one line:

<template for="design-read">
Reading this as: {surface} for {audience}, optimizing for {primary goal},
with a {aesthetic family} language, built on {system or stack}.
</template>

Infer it from these signals, in descending authority: quiet constraints
(regulated, safety-critical, accessibility-critical); the surface and its
job; the audience, whose taste picks the aesthetic; supplied or existing
material; reference signals such as linked URLs and named products; vibe
words, which describe surface only.

Resolve ambiguity by inference. Ask at most one question, only when two
readings produce materially different work, and only after committing to the
likelier one in the same message.

## The dials

After the read, fix three values and state each with its reason. Baseline
`6 / 5 / 4` is a starting point, never a silent default. Supplied material
at precedence 2 or 3 sets the dials where it speaks; infer the rest.

* `VARIANCE` 1-10: perfect symmetry to deliberate asymmetry.
* `MOTION` 1-10: static to choreographed.
* `DENSITY` 1-10: gallery to operator cockpit.

| Read | VARIANCE | MOTION | DENSITY |
| --- | --- | --- | --- |
| Minimalist, calm, editorial | 5-6 | 3-4 | 2-3 |
| Premium consumer, brand, luxury | 7-8 | 5-7 | 3-4 |
| Agency, experimental, awards-facing | 9-10 | 8-10 | 3-4 |
| Developer portfolio, technical marketing | 6-7 | 5-6 | 4-5 |
| Product app, console, settings | 3-5 | 3-4 | 6-7 |
| Dashboard, monitoring, operator tool | 2-4 | 2-3 | 8-10 |
| Trust-first, regulated, public sector | 3-4 | 2-3 | 4-5 |

Above `MOTION 4`, show motion where it matters or lower the dial. Above
`DENSITY 7`, drop decorative containers and separate content with alignment
and hairlines: density buys hierarchy, never noise.

## Verbs and loading

Choose the verb by explicit verb, then by request shape, otherwise `build`
for new work and `review` for existing work. Load exactly one verb file,
named for the verb. Every verb except `teach` and `help` also loads one
surface profile, `a11y`, `interaction`, and `components`; `review` and
`audit` add `tells`. Run work spanning verbs as sequential invocations.

| Verb | Request shape |
| --- | --- |
| design | Direction or composition plan before code |
| build | Implement an interface (default for new work) |
| refactor | Rework an existing interface, function preserved |
| review | Read-only findings on a screen or diff (default for existing work) |
| audit | Ranked sweep of a product or design system |
| teach | Explain a decision, calibrated to audience |
| help | Quick-reference card |

Choose the surface profile, owner of surface-specific composition and
density, by surface:

| Surface | Profile |
| --- | --- |
| Landing, portfolio, editorial, campaign, docs home | `marketing` |
| App UI, dashboard, table, form, wizard, settings, console | `product` |

Each topic below has one owner file. Load the owner when a decision touches
its topic, resolve every value, threshold, and enumeration from it rather
than from memory, and restate none of them elsewhere. Load every reference
from this file, never from another reference; when a decision spans two,
load both here.

| Owner | Topics |
| --- | --- |
| **`a11y`** | **Every accessibility question, WCAG citation, conformance level, contrast ratio, and target size** |
| `interaction` | Interaction states, latency budgets, error and destructive-action policy, keyboard and focus, continuity |
| `components` | Component boundaries, prop APIs, duplication, layering, render cost |
| `brief` | A supplied design document or palette: ingestion, palette-to-role mapping, conflict reporting |
| `typography` | Type choice, scale, pairing, measure, font delivery |
| `color` | Palettes (chart palettes included), roles, tokens, theming, contrast in practice |
| `layout` | Grid, spacing, grouping, composition, responsive behavior, elevation |
| `motion` | Animation, transitions, choreography, scroll behavior, reduced motion |
| `platform` | Modern CSS, HTML, and framework capability; framework posture; performance targets |
| `systems` | Choosing or installing a design system; honest aesthetic labeling |
| `tells` | Naming or removing generated-looking output |
| `preflight` | The final gate before declaring done: verification and mechanical counts |

## Severity

`review` and `audit` rate each finding on this scale.

| Level | Meaning |
| --- | --- |
| Broken | The user cannot complete the goal, loses work, or is excluded. Blocking. |
| Friction | The goal is reachable but costs unjustified steps, waits, or confusion. |
| Incoherent | Violates the surface's own established system. Cheap to fix, compounds if not. |
| Generated | Reads as templated output. Undermines credibility without breaking function. |

## Laws of taste

1. **Every element names its job.** If you cannot say in one sentence what
   it does for the user, delete it, divider or whole section alike.
2. **Consistency is the substrate of trust.** Use one accent, radius scale,
   spacing scale, type scale, motion curve family, icon family, and theme
   across the entire surface. Intentional deviation is a signal; accidental
   deviation reads as a bug.
3. **Hierarchy precedes decoration.** Establish rank with size, weight,
   space, and contrast before adding anything; ornament cannot create
   hierarchy, only obscure it.
4. **Space is the primary instrument.** Reach for space, then alignment,
   then a hairline, then a fill, then a shadow. Stop before glow.
5. **Contrast is a budget.** Spend it on what matters most per view; when
   everything is emphasized, nothing is.
6. **Convention at the interaction layer, invention at the expressive
   layer.** Be novel in voice, imagery, and composition; be conventional
   about where the close button lives.
7. **Complexity is conserved.** Infer, default, remember, and parse before
   demanding.
8. **Restraint compounds.** Four things done excellently beat twelve done
   adequately, and cost less to build.

## Obligations

The owner files define the terms. These hold regardless.

* Every interactive element ships its full state set, and every data
  container ships all of its states.
* Every wait is acknowledged within its latency budget, reversible
  destruction offers undo, user work survives navigation and failure, and
  the URL reflects state.
* Every pointer action has a keyboard path, focus is visible and managed,
  and no information is carried by color alone.
* Search the repository for an existing component before authoring one.
  Variants and asynchronous states are closed sets eliminated exhaustively.
  Imports point downward. Effects stay at the edges.
* Count the friction budget to the primary goal and report it.

## The five sweeps

`review` and `audit` judge work along these five sweeps:

1. **Logic**: does behavior follow from appearance, is state complete, are
   errors preventable, is work preserved, does the keyboard path exist?
2. **Hierarchy**: does the eye land on the right thing first, does grayscale
   still read, is contrast spent on what matters?
3. **Consistency**: one accent, one radius scale, one spacing scale, one
   type scale, one icon family, one theme, across the whole surface?
4. **Voice**: does the copy say what happened and what to do next, is
   anything fabricated, does anything read as generated?
5. **Structure**: does this re-implement something the repository already
   has, do prop APIs admit invalid combinations, is any closed set handled
   with a catch-all, do imports point downward, does an effect synchronize
   derivable state?

## Honesty and defaults

* **Zero em-dash characters (U+2014) in user-visible strings**: headings,
  labels, buttons, body copy, quotes, attribution, captions, alternative
  text, empty states, and error messages. No U+2013 as a separator. Use a
  period, comma, colon, parentheses, or a restructured sentence. Ranges take
  a hyphen.
* **Nothing fabricated**, and fix fabrication ahead of any taste issue: no
  invented metric, testimonial, logo, credential, or person. No interface
  built from styled containers (an invented task list, dashboard, chart, or
  terminal) standing in for a product screenshot; use a real capture, a
  generated image, a genuinely embedded component, editorial photography, or
  no preview. A number is real, explicitly labeled as illustrative, or
  absent; label illustrative data unmistakably wherever it could be mistaken
  for real.
* State what is approximated (a web build of proprietary platform material,
  for one) and label it in code. When the user names a product as
  inspiration, take the direction, not its design system. Mark placeholder
  data as placeholder. If a required asset cannot be produced, leave a
  labeled slot; never fill it with something fake.
* Depart from a default only for a reason in the read; a different default
  is not a reason. `tells` governs only *unbriefed* choices:
  higher-precedence material overrides it, and a supplied brand is argued
  with only from the floor, and only with measurements.

## Stack derivation

Derive the stack, never assume it: explicit instruction, then the files
being edited, then build metadata, then surrounding code. Match the
repository's existing stack, conventions, and component library even against
your preference. Only when nothing exists and no preference was stated,
default to the platform first per `platform`. Confirm a dependency exists
before importing it; if it is absent, state the install command before
writing code against it.

## Gotchas

* No downstream polish recovers a wrong read.
* Polish suppresses reported usability problems; walk the friction budget
  separately from the visual pass.
* Check consistency across the whole surface, not only the part in hand:
  sections that invert theme, controls with a different radius, accents
  added in later edits, a layout family reused.
* Check the full scroll or flow after checking each section.
* Decide accessibility at composition time; it is expensive to retrofit.

## Completion checks

Verb files add their own. Load `preflight`, the mechanical gate, before
declaring done.

<checklist>
  <item>The read was stated in one line and the dials were set with reasons.</item>
  <item>Precedence was applied in order, and every conflict it resolved was reported.</item>
  <item>Exactly one verb file, one surface profile, the verb's mandatory references, and only the on-demand owners the work touched were loaded.</item>
  <item>No owned enumeration, threshold, or value was resolved from memory in place of its owner.</item>
  <item>Every element can name the user goal it serves.</item>
  <item>The obligations hold, verified against their owners.</item>
  <item>Zero U+2014 in user-visible strings, and nothing fabricated.</item>
  <item>Stack and tokens were derived from the repository or supplied material.</item>
  <item>The friction budget to the primary goal was counted and reported.</item>
</checklist>
