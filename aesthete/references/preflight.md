# Preflight: the ship gate

Run before declaring any interface done: mechanical where a count is
defined, judgment where it is not. A gate that cannot be honestly passed
means the work is not finished. Report the result, including every gate that
did not pass.

## Mechanical counts

Count each check from the source. "Declared" means the supplied design
system's or palette's token set where one was supplied, otherwise the scales
fixed during design. Measure each count against the declaration.

| Check | Pass condition |
| --- | --- |
| U+2014 in user-visible strings | Exactly zero |
| Accessibility values or WCAG citations outside `a11y` | Exactly zero |
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

## Gates

If material was supplied, also run the completion checks in `brief`.

<checklist>
  <item>The built result matches the stated read, and the output reflects the dials: if motion is above 4, the interface moves.</item>
  <item>The obligations, honesty rules, and stack derivation in the spine hold.</item>
  <item>Every rule in `interaction` holds, including its keyboard and assistive access rules, and every rule in `components` holds.</item>
  <item>Every text and control pairing meets the thresholds in `a11y`, measured against composited backgrounds, with exemptions applied only where `a11y` allows them.</item>
  <item>Placeholder, helper, disabled, and focus-ring contrast were measured specifically.</item>
  <item>Every control's label is readable against its own background, and text over imagery has a guaranteed backing.</item>
  <item>Touch target hit areas meet the minimum in `a11y`, with spacing between neighbors.</item>
  <item>Reduced motion, reduced transparency, and forced colors are honored without losing function.</item>
  <item>Hierarchy reads correctly in grayscale.</item>
  <item>Between-group spacing clearly exceeds within-group spacing.</item>
  <item>Cards enclose discrete objects the user acts on.</item>
  <item>Narrow layouts were designed and verified, with stacking order matching DOM order.</item>
  <item>Space is reserved for every asynchronous element, so nothing shifts after paint.</item>
  <item>One theme holds across the surface, set once at the root; both themes were opened and reviewed.</item>
  <item>Theme follows the system preference with no stored state, unless the user asked for a toggle.</item>
  <item>Body measure sits between roughly 45 and 75 characters; type sizes are in relative units.</item>
  <item>Aligned or updating numbers use tabular figures.</item>
  <item>Fonts are self-hosted or pipelined, subset, swapped, and metric-matched to their fallback.</item>
  <item>One motion curve family; every animation passes the one-sentence justification test.</item>
  <item>Every visible string was re-read, and anything grammatically broken, referentially unclear, or clever-but-wrong was rewritten.</item>
  <item>Assets are real, generated, or left as labeled slots, with required assets named in the response.</item>
  <item>One label per call-to-action intent across the surface, fitting on one line at desktop.</item>
  <item>Interactivity is isolated to leaves; no continuous value is driven through render state.</item>
  <item>Only compositor-friendly properties animate; observers, timelines, and contexts are torn down.</item>
  <item>Native elements and platform APIs were used where they suffice; any custom control carries its full keyboard and assistive contract.</item>
  <item>Support status was verified for every platform capability relied on.</item>
  <item>Paint, interaction, and layout-stability targets are plausibly met.</item>
</checklist>

## Reporting

State the outcome in this shape:

<template for="preflight">
Preflight: {passed | failed}
Counts: {any count that is not at its pass value}
Unresolved: {gates that could not be honestly ticked, and why}
Assets required: {labeled slots still needing real content}
Friction budget: {n} steps to {primary goal}
Not verified: {anything requiring a running application, real data, or
assistive technology testing}
</template>

An honest failure report is a successful preflight. Claiming a pass that was
not verified is the only way to fail this gate outright.
