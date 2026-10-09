# Preflight: the ship gate

Run before declaring any interface done: mechanical where count is defined,
judgment where not. Gate that cannot be honestly passed: work not finished.
Report result, including every gate that did not pass.

## Mechanical counts

Count each check from source. "Declared": supplied design system's or
palette's token set where one was supplied, otherwise scales fixed during
design. Measure each count against declaration.

| Check | Pass condition |
| --- | --- |
| U+2014 in user-visible strings | Exactly zero |
| Accessibility values or WCAG citations outside `a11y` | Exactly zero |
| U+2013 as separator | Exactly zero |
| Accent colors used | Exactly declared set, no additions |
| Radius values used | From declared scale only |
| Spacing values used | From declared scale only |
| Type sizes used | From declared scale only |
| Color values not traceable to token | Exactly zero |
| Icon families | Exactly one, at one weight |
| Component systems in tree | Exactly one |
| Animation systems per component tree | Exactly one |
| Section micro-labels | At most one per three sections |
| Consecutive image-and-text split sections | At most two |
| Horizontally scrolling marquees | At most one per page |
| Layout families reused | Zero repeats |
| Grid cells without content | Exactly zero |
| Raw scroll event subscriptions | Exactly zero |
| Undeclared imported dependencies | Exactly zero |
| Implementations per primitive concept | Exactly one |
| Catch-all branches over closed variant set | Exactly zero |
| Imports pointing upward through layer ladder | Exactly zero |
| Domain types below pattern layer | Exactly zero |
| Effects whose body only copies state into state | Exactly zero |
| Array indices used as keys in reorderable lists | Exactly zero |

## Gates

Material supplied: also run completion checks in `brief`.

<checklist>
  <item>Built result matches stated read; output reflects dials: motion above 4 means interface moves.</item>
  <item>Spine's obligations, honesty rules, stack derivation hold.</item>
  <item>Every rule in `interaction` holds, including its keyboard and assistive access rules; every rule in `components` holds.</item>
  <item>Every text and control pairing meets thresholds in `a11y`, measured against composited backgrounds, exemptions applied only where `a11y` allows.</item>
  <item>Placeholder, helper, disabled, focus-ring contrast measured specifically.</item>
  <item>Every control's label readable against its own background; text over imagery has guaranteed backing.</item>
  <item>Touch target hit areas meet minimum in `a11y`, with spacing between neighbors.</item>
  <item>Reduced motion, reduced transparency, forced colors honored without losing function.</item>
  <item>Hierarchy reads correctly in grayscale.</item>
  <item>Between-group spacing clearly exceeds within-group spacing.</item>
  <item>Cards enclose discrete objects user acts on.</item>
  <item>Narrow layouts designed and verified, stacking order matching DOM order.</item>
  <item>Space reserved for every asynchronous element; nothing shifts after paint.</item>
  <item>One theme across surface, set once at root; both themes opened and reviewed.</item>
  <item>Theme follows system preference with no stored state, unless user asked for toggle.</item>
  <item>Body measure roughly 45 to 75 characters; type sizes in relative units.</item>
  <item>Aligned or updating numbers use tabular figures.</item>
  <item>Fonts self-hosted or pipelined, subset, swapped, metric-matched to fallback.</item>
  <item>One motion curve family; every animation passes one-sentence justification test.</item>
  <item>Every visible string re-read; anything grammatically broken, referentially unclear, or clever-but-wrong rewritten.</item>
  <item>Assets real, generated, or left as labeled slots; required assets named in response.</item>
  <item>One label per call-to-action intent across surface, fitting on one line at desktop.</item>
  <item>Interactivity isolated to leaves; no continuous value driven through render state.</item>
  <item>Only compositor-friendly properties animate; observers, timelines, contexts torn down.</item>
  <item>Native elements and platform APIs used where they suffice; any custom control carries full keyboard and assistive contract.</item>
  <item>Support status verified for every platform capability relied on.</item>
  <item>Paint, interaction, layout-stability targets plausibly met.</item>
</checklist>

## Reporting

State outcome in this shape:

<template for="preflight">
Preflight: {passed | failed}
Counts: {any count that is not at its pass value}
Unresolved: {gates that could not be honestly ticked, and why}
Assets required: {labeled slots still needing real content}
Friction budget: {n} steps to {primary goal}
Not verified: {anything requiring a running application, real data, or
assistive technology testing}
</template>

Honest failure report is successful preflight. Claiming unverified pass is
only way to fail this gate outright.
