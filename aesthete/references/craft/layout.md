# Craft: layout

Space, alignment, and grouping do the work; use borders and boxes only when
those signals are insufficient.

## Space

* Use one geometric spacing scale for every gap, padding, and margin, with
  fewer than nineteen distinct values.
* Proximity is the strongest grouping signal and costs nothing. Space
  between groups must clearly exceed space within a group; most confusing
  layouts apply uniform spacing to non-uniform content.
* Space belongs to the container. Prefer gap on a layout container over
  margins on items, so removing an item never leaves a hole.
* Section spacing, block spacing, and element spacing form three clearly
  distinct tiers. Two tiers close in value read as an accident.

## Grouping ladder

Reach in this order and stop at the first that works:

1. **Space.** Separate the groups.
2. **Alignment.** Shared edges imply relationship without any mark.
3. **Hairline.** A single divider where a boundary must be explicit.
4. **Surface tint.** A subtle background change for a distinct region.
5. **Border.** An outline when a region must be enclosed.
6. **Elevation.** A shadow when something floats above the plane.

A card combines rungs four through six. Use it only when the content is a
discrete, self-contained object the user acts on as a unit. When the content
is text, use space and alignment.

## Grid and structure

* Use a real two-dimensional grid for two-dimensional layouts. Percentage
  arithmetic inside a flex container to fake columns breaks at every gap
  change.
* Constrain overall width so line lengths stay readable on large displays,
  and constrain text blocks independently of their containers.
* Optical alignment beats mathematical alignment when they disagree.
  Punctuation, icons, and round shapes need small manual corrections to look
  aligned.
* Align every relevant element to a consistent edge; correct a composition
  with four different left edges.
* Use asymmetry for deliberate weighting and tension.

## Responsive behavior

* Design the narrow view as a first-class layout; on most products it is the
  majority of use.
* Prefer intrinsic sizing and content-driven wrapping over viewport
  breakpoints where the platform supports it. A component that responds to
  its own container works in a sidebar, a modal, and a full-width region
  without three sets of breakpoint overrides.
* Declare every multi-column region's narrow behavior in the same place as
  its wide behavior. Framework defaults do not cover every narrow layout.
* When things stack, verify the stacked reading order is the intended
  priority order and matches the DOM order, so keyboard and assistive
  traversal agree with the visual sequence.
* Use dynamic viewport units for full-height regions so mobile browser
  interface changes do not cause jumps.
* Touch targets meet the minimum size `a11y` defines, with spacing between
  adjacent targets, regardless of the visual size of the mark inside them.

## Layering

* Use a named, documented elevation scale with few levels: base, raised,
  sticky, overlay, modal, notification. Avoid arbitrary stacking values,
  which conflict and invite escalating numbers.
* Establish stacking contexts deliberately. Transforms, filters, and opacity
  create them implicitly, the usual cause of an overlay trapped behind its
  neighbor.
* Sticky regions must not obscure focused elements when a keyboard user tabs
  behind them, and must reserve their space so content does not jump.

## Stability

Prevent shifts after paint. Reserve dimensions for images, fonts, media,
embeds, and any region that loads late. Skeletons match the real layout's
dimensions. Insert notifications and banners in reserved space or as
overlays. Preserve the reader's position after reading begins.
