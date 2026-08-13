# Craft: layout

Layout is where hierarchy becomes visible. Space, alignment, and grouping do
the work; borders and boxes are what you reach for when the spacing failed.

## Space

* One spacing scale, geometric rather than arbitrary, used for every gap,
  padding, and margin. A layout containing nineteen distinct spacing values
  has no system.
* Proximity is the strongest grouping signal available and costs nothing.
  Space between groups must clearly exceed space within a group. Most
  confusing layouts are uniform spacing applied to non-uniform content.
* Space belongs to the container, not sprinkled onto children. Prefer gap on
  a layout container over margins on items, so removing an item never leaves
  a hole.
* Vertical rhythm is a cadence: section spacing, block spacing, and element
  spacing form three clearly distinct tiers. Two tiers that are close in
  value read as an accident.

## Grouping ladder

Reach in this order and stop at the first that works:

1. **Space.** Separate the groups.
2. **Alignment.** Shared edges imply relationship without any mark.
3. **Hairline.** A single divider where a boundary must be explicit.
4. **Surface tint.** A subtle background change for a genuinely distinct
   region.
5. **Border.** An outline when a region must be enclosed.
6. **Elevation.** A shadow when something genuinely floats above the plane.

A card is rungs four through six at once. Use it only when the content is a
discrete, self-contained object the user acts on as a unit. A page of cards
containing text is a page that skipped rungs one and two.

## Grid and structure

* Use a real two-dimensional grid for two-dimensional layouts. Percentage
  arithmetic inside a flex container to fake columns is fragile and breaks
  at every gap change.
* Constrain overall width so line lengths stay readable on large displays,
  and constrain text blocks independently of their containers.
* Optical alignment beats mathematical alignment when they disagree.
  Punctuation, icons, and round shapes need small manual corrections to look
  aligned.
* Align to a consistent edge. A composition with four different left edges
  reads as unresolved regardless of how deliberate it was.
* Asymmetry is a composition, not an absence of one. High variance means
  deliberate weighting and tension, not random offsets.

## Responsive behavior

* Design the narrow view as a first-class layout, not as a degradation. On
  most products it is the majority of use.
* Prefer intrinsic sizing and content-driven wrapping over viewport
  breakpoints where the platform supports it. A component that responds to
  its own container works in a sidebar, a modal, and a full-width region
  without three sets of breakpoint overrides.
* Every multi-column region declares its narrow behavior in the same place
  it declares its wide behavior. Assuming the framework handles it is how
  narrow layouts break.
* Order matters when things stack. Verify the stacked reading order is the
  intended priority order, and that it matches the DOM order so keyboard and
  assistive traversal agree with the visual sequence.
* Use dynamic viewport units for full-height regions so mobile browser
  interface changes do not cause jumps.
* Touch targets need a comfortable minimum hit area with spacing between
  adjacent targets, regardless of the visual size of the mark inside them.

## Layering

* A named, documented elevation scale with a small number of levels: base,
  raised, sticky, overlay, modal, notification. Arbitrary stacking values
  scattered through components produce conflicts that get fixed by escalating
  numbers until nothing is predictable.
* Establish stacking contexts deliberately. Transforms, filters, and opacity
  create them implicitly, which is the usual cause of an overlay trapped
  behind its neighbor.
* Sticky regions must not obscure focused elements when a keyboard user tabs
  behind them, and must reserve their space so content does not jump.

## Stability

Nothing may shift after paint. Reserve dimensions for images, media,
embeds, and any region that loads late. Skeletons match the real layout's
dimensions, not an approximation. Insert notifications and banners in
reserved space or as overlays, never by pushing the page down after the user
has started reading.

## Completion checks

<validation_checklist>
  <item>One spacing scale, applied through container gaps rather than child margins.</item>
  <item>Between-group spacing clearly exceeds within-group spacing everywhere.</item>
  <item>The grouping ladder was climbed in order; cards enclose discrete objects only.</item>
  <item>Two-dimensional layouts use a real grid, with text width constrained independently.</item>
  <item>Narrow layouts are designed, declared alongside wide behavior, and their stacking order matches DOM order.</item>
  <item>Touch targets meet a comfortable minimum with spacing between neighbors.</item>
  <item>A named elevation scale is used and no arbitrary stacking values remain.</item>
  <item>Space is reserved for every late-loading element and nothing shifts after paint.</item>
</validation_checklist>
