# Preflight: the ship gate

Run before declaring any interface done. Mechanical where a count is
defined, judgment where it is not. A gate that cannot be honestly passed
means the work is not finished, not that the gate is too strict.

Report the result. Do not silently pass.

## Mechanical counts

Each of these is countable in the source. Count, do not estimate.

Where a design system or palette was supplied, "declared" means its token
set. Where none was, it means the scales fixed during design. A count is
measured against the declaration, never against a preference.

| Check | Pass condition |
| --- | --- |
| U+2014 in user-visible strings | Exactly zero |
| Accessibility values or WCAG citations outside a11y.md | Exactly zero |
| U+2013 as a separator | Exactly zero |
| Accent colors used | Exactly the declared set, no additions |
| Radius values used | Drawn from the declared scale only |
| Spacing values used | Drawn from the declared scale only |
| Type sizes used | Drawn from the declared scale only |
| Color values not traceable to a token | Exactly zero |
| Icon families | Exactly one, at one weight |
| Component systems in the tree | Exactly one |
| Animation systems per component tree | Exactly one |
| Section micro-labels | At most one per three sections |
| Consecutive image-and-text split sections | At most two |
| Horizontally scrolling marquees | At most one per page |
| Layout families reused | Zero repeats |
| Grid cells without content | Exactly zero |
| Raw scroll event subscriptions | Exactly zero |
| Undeclared imported dependencies | Exactly zero |
| Implementations per primitive concept | Exactly one |
| Catch-all branches over a closed variant set | Exactly zero |
| Imports pointing upward through the layer ladder | Exactly zero |
| Domain types below the pattern layer | Exactly zero |
| Effects whose body only copies state into state | Exactly zero |
| Array indices used as keys in reorderable lists | Exactly zero |

## Supplied material

Skip only if nothing was supplied.

- [ ] Precedence applied in order: the palette overrode the document's
      colors, the document overrode this skill's defaults, and the
      accessibility floor overrode everything.
- [ ] Every supplied token pairing actually used was measured for contrast,
      not assumed, including secondary text on tinted surfaces.
- [ ] Every floor conflict was resolved by derivation and reported, with the
      brand preserved wherever the threshold allowed.
- [ ] Accessibility claims made by the document were verified against the
      specification rather than inherited.
- [ ] Gaps the document left were derived from its own logic and reported.

## Direction

- [ ] The design read was stated, and the built result matches it.
- [ ] Dials were set from the read with reasons, and the output reflects
      them. If motion is above 4, the interface actually moves.
- [ ] Every element can name the user goal it serves.
- [ ] The friction budget to the primary goal was counted and reported.

## Interaction

- [ ] Every interactive element and every data container ships every state
      craft/interaction.md defines, encoded as one closed set.
- [ ] No loader appears for a response under the flash threshold, and every
      wait past it is acknowledged at the point of action.
- [ ] Input is parsed liberally; nothing is rejected for formatting the
      system could normalize.
- [ ] Errors preserve entry, sit adjacent to their cause, name the fix, and
      move focus to the first failure.
- [ ] Reversible destructive actions offer undo; irreversible ones name the
      exact object and consequence.
- [ ] User work survives navigation, refresh, back, and server failure.
- [ ] URL reflects record, tab, filter, sort, and page state.

## Accessibility

- [ ] Every text and control pairing meets the thresholds in a11y.md,
      measured against composited backgrounds, with exemptions applied only
      where a11y.md allows them.
- [ ] Placeholder, helper, disabled, and focus-ring contrast were measured
      specifically.
- [ ] Every control's label is readable against its own background, and text
      over imagery has a guaranteed backing.
- [ ] Focus is always visible, never suppressed, and never obscured by
      sticky regions.
- [ ] Full keyboard parity; focus order matches visual order; dialogs trap
      and return focus; escape dismisses; backgrounds are inert.
- [ ] Touch target hit areas meet the minimum in a11y.md, with spacing
      between neighbors.
- [ ] No information is carried by color alone.
- [ ] Every drag interaction has a non-drag alternative.
- [ ] Reduced motion, reduced transparency, and forced colors are honored
      without losing function.
- [ ] Asynchronous changes are announced through a live region.

## Composition

- [ ] Hierarchy reads correctly in grayscale.
- [ ] Between-group spacing clearly exceeds within-group spacing.
- [ ] Cards enclose discrete objects the user acts on, not arbitrary text.
- [ ] Narrow layouts were designed and verified, with stacking order
      matching DOM order.
- [ ] Nothing shifts after paint; space is reserved for every asynchronous
      element.
- [ ] One theme holds across the surface, set once at the root.
- [ ] Both themes were opened and reviewed, not just the one being built in.

## Craft

- [ ] Body measure sits between roughly 45 and 75 characters; type sizes are
      in relative units.
- [ ] Aligned or updating numbers use tabular figures.
- [ ] Fonts are self-hosted or pipelined, subset, swapped, and
      metric-matched to their fallback.
- [ ] One motion curve family; every animation passes the one-sentence
      justification test.

## Content

- [ ] Every visible string was re-read, and anything grammatically broken,
      referentially unclear, or clever-but-wrong was rewritten.
- [ ] Numbers are real, explicitly labeled as illustrative, or absent.
- [ ] No fabricated product interface, logo, testimonial, metric, credential,
      or person.
- [ ] Assets are real, generated, or left as labeled slots, with required
      assets named in the response.
- [ ] One label per call-to-action intent across the surface, fitting on one
      line at desktop.

## Engineering

- [ ] Stack, tokens, and component library were derived from the repository,
      and the repository was searched before any component was authored.
- [ ] Variants and asynchronous states are closed sets eliminated
      exhaustively, so omitting a state fails the build.
- [ ] Each component varies along one axis; no prop switches which subtree
      renders and no prop exists for a single call site.
- [ ] Call sites adjust position, not identity; new looks became variants.
- [ ] No lookup runs inside a row loop; expensive construction is hoisted.
- [ ] Interactivity is isolated to leaves; no continuous value is driven
      through render state.
- [ ] Only compositor-friendly properties animate; observers, timelines, and
      contexts are torn down.
- [ ] Native elements and platform APIs were used where they suffice; any
      custom control carries its full keyboard and assistive contract.
- [ ] Support status was verified for every platform capability relied on.
- [ ] Paint, interaction, and layout-stability targets are plausibly met.

## Reporting

State the outcome in this shape:

<preflight_report>
Preflight: {passed | failed}
Counts: {any count that is not at its pass value}
Unresolved: {gates that could not be honestly ticked, and why}
Assets required: {labeled slots still needing real content}
Friction budget: {n} steps to {primary goal}
Not verified: {anything requiring a running application, real data, or
assistive technology testing}
</preflight_report>

An honest failure report is a successful preflight. Claiming a pass that was
not verified is the only way to fail this gate outright.
