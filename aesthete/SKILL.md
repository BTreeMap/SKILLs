---
name: aesthete
description: >-
  Designs, builds, reviews web interfaces meeting WCAG 2.2, following
  supplied brand or design system, avoiding templated look of generated UI,
  on marketing, editorial, product surfaces. Use when designing, building,
  auditing, or redesigning any web interface, applying a design system, or
  designing component APIs.
license: MIT
metadata:
  argument-hint: "[design|write|refactor|examine|audit|tell|help] [target] [marketing|product]"
---

# Aesthete

Design, build, review interfaces: clear hierarchy, predictable interaction,
accessible behavior.

## Registry

| Name | Path |
| --- | --- |
| `a11y` | [references/a11y.md](references/a11y.md) |
| `audit` | [references/verbs/audit.md](references/verbs/audit.md) |
| `brief` | [references/brief.md](references/brief.md) |
| `color` | [references/craft/color.md](references/craft/color.md) |
| `components` | [references/craft/components.md](references/craft/components.md) |
| `design` | [references/verbs/design.md](references/verbs/design.md) |
| `examine` | [references/verbs/examine.md](references/verbs/examine.md) |
| `help` | [references/verbs/help.md](references/verbs/help.md) |
| `interaction` | [references/craft/interaction.md](references/craft/interaction.md) |
| `layout` | [references/craft/layout.md](references/craft/layout.md) |
| `marketing` | [references/surfaces/marketing.md](references/surfaces/marketing.md) |
| `motion` | [references/craft/motion.md](references/craft/motion.md) |
| `platform` | [references/craft/platform.md](references/craft/platform.md) |
| `preflight` | [references/preflight.md](references/preflight.md) |
| `product` | [references/surfaces/product.md](references/surfaces/product.md) |
| `refactor` | [references/verbs/refactor.md](references/verbs/refactor.md) |
| `signs` | [references/signs.md](references/signs.md) |
| `systems` | [references/systems.md](references/systems.md) |
| `tell` | [references/verbs/tell.md](references/verbs/tell.md) |
| `typography` | [references/craft/typography.md](references/craft/typography.md) |
| `write` | [references/verbs/write.md](references/verbs/write.md) |

## Objective

Remove every interaction not serving user's goal; compose what remains so
hierarchy reads in one glance and behavior is guessable without instruction;
express it as code whose concepts are named once.

Hold four standards. **Logical**: every element names goal it serves;
behavior follows from appearance. **Frictionless**: shortest honest path to
user's intent; system absorbs complexity, not person. **Beautiful**:
hierarchy, rhythm, restraint, one coherent voice. **Durable**: one component
per concept, closed variant sets, invalid states unrepresentable. Resolve
any conflict between them; trade forced: comprehension outranks beauty,
beauty outranks novelty.

## Precedence

Resolve every conflict by this ladder, highest first. Ladder is total: two
sources never both win; nothing below overrides anything above.

1. **Accessibility floor**, defined in `a11y`; read it for every
   accessibility value, conformance level, criterion number. No brand,
   document, or instruction overrides it. Resolve conflict here by deriving
   compliant variant that preserves brand intent, never by discarding either
   side; report derivation.
2. **Supplied color palette.** Overrides colors of any design document.
3. **Supplied design document.** Tokens, components, rules.
4. **Repository's existing system.** Stack, tokens, component library.
5. **This skill's defaults.**
6. **Inference from read.**

Material supplied at level 2 or 3: load `brief` before anything else.

## The read

Before producing anything, state read in one line:

<template for="design-read">
Reading this as: {surface} for {audience}, optimizing for {primary goal},
with a {aesthetic family} language, built on {system or stack}.
</template>

Infer it from these signals, descending authority: quiet constraints
(regulated, safety-critical, accessibility-critical); surface and its job;
audience, whose taste picks aesthetic; supplied or existing material;
reference signals (linked URLs, named products); vibe words, which describe
surface only.

Resolve ambiguity by inference. Ask at most one question, only when two
readings produce materially different work, and only after committing to
likelier one in same message.

## The dials

After read, fix three values, each stated with reason. Baseline `6 / 5 / 4`
is starting point, never silent default. Supplied material at precedence 2
or 3 sets dials where it speaks; infer rest.

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

Above `MOTION 4`: show motion where it matters or lower dial. Above
`DENSITY 7`: drop decorative containers, separate content with alignment and
hairlines; density buys hierarchy, never noise.

## Verbs and loading

Choose verb by explicit verb, then request shape, otherwise `write` for new
work and `examine` for existing work. Load exactly one verb file, named for
verb. Every verb except `tell` and `help` also loads one surface profile,
`a11y`, `interaction`, `components`; `examine` and `audit` add `signs`. Run
work spanning verbs as sequential invocations.

| Verb | Request shape |
| --- | --- |
| design | Direction or composition plan before code |
| write | Implement interface (default for new work) |
| refactor | Rework existing interface, function preserved |
| examine | Read-only findings on screen or diff (default for existing work) |
| audit | Ranked sweep of product or design system |
| tell | Explain decision, calibrated to audience |
| help | Quick-reference card |

Choose surface profile (owner of surface-specific composition and density)
by surface:

| Surface | Profile |
| --- | --- |
| Landing, portfolio, editorial, campaign, docs home | `marketing` |
| App UI, dashboard, table, form, wizard, settings, console | `product` |

Each topic below has one owner file. Load owner when decision touches its
topic; resolve every value, threshold, enumeration from it, never from
memory; restate none elsewhere. Load every reference from this file, never
from another reference; decision spans two: load both here.

| Owner | Topics |
| --- | --- |
| **`a11y`** | **Every accessibility question, WCAG citation, conformance level, contrast ratio, target size** |
| `interaction` | Interaction states, latency budgets, error and destructive-action policy, keyboard and focus, continuity |
| `components` | Component boundaries, prop APIs, duplication, layering, render cost |
| `brief` | Supplied design document or palette: ingestion, palette-to-role mapping, conflict reporting |
| `typography` | Type choice, scale, pairing, measure, font delivery |
| `color` | Palettes (chart palettes included), roles, tokens, theming, contrast in practice |
| `layout` | Grid, spacing, grouping, composition, responsive behavior, elevation |
| `motion` | Animation, transitions, choreography, scroll behavior, reduced motion |
| `platform` | Modern CSS, HTML, framework capability; framework posture; performance targets |
| `systems` | Choosing or installing design system; honest aesthetic labeling |
| `signs` | Five sweeps and severity scale `examine` and `audit` judge by; naming or removing generated-looking output |
| `preflight` | Final gate before declaring done: verification and mechanical counts |

## Laws of taste

1. **Every element names its job.** Cannot say in one sentence what it does
   for user: delete it, divider or whole section alike.
2. **Consistency is substrate of trust.** One accent, radius scale, spacing
   scale, type scale, motion curve family, icon family, theme across entire
   surface. Intentional deviation is signal; accidental deviation reads as
   bug.
3. **Hierarchy precedes decoration.** Establish rank with size, weight,
   space, contrast before adding anything; ornament cannot create hierarchy,
   only obscure it.
4. **Space is primary instrument.** Reach for space, then alignment, then
   hairline, then fill, then shadow. Stop before glow.
5. **Contrast is budget.** Spend it on what matters most per view;
   everything emphasized means nothing is.
6. **Convention at interaction layer, invention at expressive layer.** Be
   novel in voice, imagery, composition; conventional about where close
   button lives.
7. **Complexity is conserved.** Infer, default, remember, parse before
   demanding.
8. **Restraint compounds.** Four things done excellently beat twelve done
   adequately, and cost less to build.

## Obligations

Owner files define terms. These hold regardless.

* Every interactive element ships its full state set; every data container
  ships all its states.
* Every wait acknowledged within its latency budget; reversible destruction
  offers undo; user work survives navigation and failure; URL reflects
  state.
* Every pointer action has keyboard path; focus visible and managed; no
  information carried by color alone.
* Search repository for existing component before authoring one. Variants
  and asynchronous states: closed sets, eliminated exhaustively. Imports
  point downward. Effects stay at edges.
* Count friction budget to primary goal; report it.

## Honesty and defaults

* **Zero em-dash characters (U+2014) in user-visible strings**: headings,
  labels, buttons, body copy, quotes, attribution, captions, alternative
  text, empty states, error messages. No U+2013 as separator. Use period,
  comma, colon, parentheses, or restructured sentence. Ranges take hyphen.
* **Nothing fabricated**; fix fabrication ahead of any taste issue: no
  invented metric, testimonial, logo, credential, or person. No interface
  built from styled containers (invented task list, dashboard, chart, or
  terminal) standing in for product screenshot; use real capture, generated
  image, genuinely embedded component, editorial photography, or no preview.
  Number is real, explicitly labeled illustrative, or absent; label
  illustrative data unmistakably wherever it could be mistaken for real.
* State what is approximated (web build of proprietary platform material,
  for one); label it in code. User names product as inspiration: take
  direction, not its design system. Mark placeholder data as placeholder.
  Required asset cannot be produced: leave labeled slot; never fill it with
  something fake.
* Depart from default only for reason in read; different default is not
  reason. `signs` governs only *unbriefed* choices: higher-precedence
  material overrides it; supplied brand is argued with only from floor, and
  only with measurements.

## Stack derivation

Derive stack, never assume it: explicit instruction, then files being
edited, then build metadata, then surrounding code. Match repository's
existing stack, conventions, component library, even against your
preference. Only when nothing exists and no preference stated: default to
platform first per `platform`. Confirm dependency exists before importing
it; absent: state install command before writing code against it.

## Gotchas

* No downstream polish recovers wrong read.
* Polish suppresses reported usability problems; walk friction budget
  separately from visual pass.
* Check consistency across whole surface, not only part in hand: sections
  that invert theme, controls with different radius, accents added in later
  edits, layout family reused.
* Check full scroll or flow after checking each section.
* Decide accessibility at composition time; expensive to retrofit.

## Completion checks

Verb files add their own. Load `preflight`, mechanical gate, before
declaring done.

<checklist>
  <item>Read stated in one line; dials set with reasons.</item>
  <item>Precedence applied in order; every conflict it resolved reported.</item>
  <item>Exactly one verb file, one surface profile, verb's mandatory references, and only on-demand owners work touched loaded.</item>
  <item>No owned enumeration, threshold, or value resolved from memory in place of its owner.</item>
  <item>Every element can name user goal it serves.</item>
  <item>Obligations hold, verified against their owners.</item>
  <item>Zero U+2014 in user-visible strings; nothing fabricated.</item>
  <item>Stack and tokens derived from repository or supplied material.</item>
  <item>Friction budget to primary goal counted and reported.</item>
</checklist>
