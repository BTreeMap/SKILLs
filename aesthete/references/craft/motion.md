# Craft: motion

Motion exists to explain change. Animation not helping user understand what
happened, what is happening, or what to do next adds work every visit.

## The justification test

Before adding any animation, state in one sentence what it communicates.
Only valid answers:

* **Continuity**: this element is same object that was over there.
* **Hierarchy**: look here first.
* **Causality**: this happened because you did that.
* **Progress**: work underway, this much remains.
* **Narrative**: sequence has order user should follow.

Sentence does not come: remove animation. Animation library only when it
supplies needed capability.

## Duration and curve

* Small, local changes: fast enough to feel immediate. Hover and press
  feedback at short end.
* Elements entering or leaving: moderate, asymmetric. Exits faster than
  entrances; user already decided.
* Large surfaces crossing screen: longer, but brief. Past roughly half a
  second in product interface costs user time every repetition.
* Distance scales duration, but sublinearly.
* Eased curves decelerating into rest. Linear motion reads mechanical except
  for continuous ambient movement and progress indicators. Spring behavior
  suits direct manipulation, where gesture should feel physically connected.
  One curve family per product.

## Choreography

* Stagger to show relationship and order, small delay per item; cap total so
  last item does not arrive after user started reading first.
* Animate parent or child, not both in competing ways.
* Same object persists across state or route change: animate it to preserve
  continuity.
* Show content user is waiting for without entry animation.

## Scroll-linked motion

* Reveal-on-enter needs only intersection observation or platform's
  view-progress timeline; scroll-orchestration library for simple reveals is
  over-tooling.
* Reveals fire once, not on every scroll back through section.
* Pin sequence when section's top reaches viewport top. Starting animation
  before pin shows half a frame of intended composition.
* Stacked-card sequence: every card except last pins; each card's recede
  transform driven by next card's arrival, not its own progress.
* Horizontal pan: wrapper pins, inner track translates, scroll length set to
  track's overflow width so pan finishes exactly as pin releases. Recompute
  on resize.
* Scroll hijacking removes control from user. Budget at most one such
  section; keep it off surfaces where user has task to complete.
* **Drive scroll-linked motion with scroll-driven timelines, intersection
  observer, or frame-external animation values.** Raw scroll events and
  render state rerun work every frame, collapse on mid-range hardware.

## Restraint

* Infinite loops for live state only. Ambient perpetual motion in periphery
  competes for attention permanently, returns nothing.
* At most one attention-seeking device per view.
* Motion never blocks input: user can always click through, scroll past, or
  skip.
* Animation must handle being reversed or restarted mid-flight without
  snapping.

## Reduced motion is a requirement

Honor reduced-motion preference: replace movement with fade or instant
change, disable parallax and scroll hijacking entirely, stop infinite loops,
keep every state transition legible without animation.

Reduced motion means less movement, never less function. Never gate content,
state changes, or affordances behind animation preference disables. Check
preference at point of use so mid-session change takes effect.

Respect reduced-transparency and forced-colors preferences on same
principle, with solid, high-contrast fallback for any material effect.

## Performance

* Animate only compositor-friendly properties: transform and opacity.
  Animating geometry forces layout every frame.
* Promote only what animates; blanket promotion consumes memory, can degrade
  what it was meant to help.
* Grain, noise, heavy filters on fixed, non-interactive overlay layer; in
  scrolling container they repaint continuously.
* Lazy-load animation libraries and heavy scenes not needed for first view;
  tear down every observer, timeline, context on unmount.
