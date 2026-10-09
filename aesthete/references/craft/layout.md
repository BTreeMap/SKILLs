# Craft: layout

Space, alignment, grouping do the work; borders and boxes only when those
signals are insufficient.

## Space

* One geometric spacing scale for every gap, padding, margin, fewer than
  nineteen distinct values.
* Proximity is strongest grouping signal and costs nothing. Space between
  groups must clearly exceed space within group; most confusing layouts
  apply uniform spacing to non-uniform content.
* Space belongs to container. Prefer gap on layout container over margins on
  items, so removing item never leaves hole.
* Section, block, element spacing: three clearly distinct tiers. Two tiers
  close in value read as accident.

## Grouping ladder

Reach in this order; stop at first that works:

1. **Space.** Separate groups.
2. **Alignment.** Shared edges imply relationship without any mark.
3. **Hairline.** Single divider where boundary must be explicit.
4. **Surface tint.** Subtle background change for distinct region.
5. **Border.** Outline when region must be enclosed.
6. **Elevation.** Shadow when something floats above plane.

Card combines rungs four through six. Use only when content is discrete,
self-contained object user acts on as unit. Content is text: space and
alignment.

## Grid and structure

* Real two-dimensional grid for two-dimensional layouts. Percentage
  arithmetic inside flex container faking columns breaks at every gap
  change.
* Constrain overall width so line lengths stay readable on large displays;
  constrain text blocks independently of containers.
* Optical alignment beats mathematical alignment when they disagree.
  Punctuation, icons, round shapes need small manual corrections to look
  aligned.
* Align every relevant element to consistent edge; correct composition with
  four different left edges.
* Asymmetry for deliberate weighting and tension.

## Responsive behavior

* Design narrow view as first-class layout; on most products it is majority
  of use.
* Prefer intrinsic sizing and content-driven wrapping over viewport
  breakpoints where platform supports it. Component responding to its own
  container works in sidebar, modal, full-width region without three sets of
  breakpoint overrides.
* Declare every multi-column region's narrow behavior in same place as its
  wide behavior. Framework defaults do not cover every narrow layout.
* Things stack: verify stacked reading order is intended priority order and
  matches DOM order, so keyboard and assistive traversal agree with visual
  sequence.
* Dynamic viewport units for full-height regions, so mobile browser
  interface changes cause no jumps.
* Touch targets meet minimum size `a11y` defines, with spacing between
  adjacent targets, regardless of visual size of mark inside.

## Layering

* Named, documented elevation scale with few levels: base, raised, sticky,
  overlay, modal, notification. Avoid arbitrary stacking values: they
  conflict and invite escalating numbers.
* Establish stacking contexts deliberately. Transforms, filters, opacity
  create them implicitly: usual cause of overlay trapped behind neighbor.
* Sticky regions must not obscure focused elements when keyboard user tabs
  behind them; must reserve their space so content does not jump.

## Stability

Prevent shifts after paint. Reserve dimensions for images, fonts, media,
embeds, any region that loads late. Skeletons match real layout's
dimensions. Insert notifications and banners in reserved space or as
overlays. Preserve reader's position after reading begins.
