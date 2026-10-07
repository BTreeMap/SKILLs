# Craft: motion

Motion exists to explain change. An animation that does not help the user
understand what happened, what is happening, or what to do next adds work on
every visit.

## The justification test

Before adding any animation, state in one sentence what it communicates. The
only valid answers:

* **Continuity**: this element is the same object that was over there.
* **Hierarchy**: look here first.
* **Causality**: this happened because you did that.
* **Progress**: work is underway and this is how much remains.
* **Narrative**: this sequence has an order the user should follow.

If the sentence does not come, remove the animation. Use an animation
library only when it supplies a needed capability.

## Duration and curve

* Small, local changes: fast enough to feel immediate. Hover and press
  feedback belongs at the short end.
* Elements entering or leaving: moderate, and asymmetric. Exits run faster
  than entrances, because the user has already decided.
* Large surfaces crossing the screen: longer, but brief. Anything past
  roughly half a second in a product interface costs the user time on every
  repetition.
* Distance scales duration, but sublinearly.
* Use eased curves that decelerate into rest. Linear motion reads mechanical
  except for continuous ambient movement and progress indicators. Spring
  behavior suits direct manipulation, where the gesture should feel
  physically connected. Use one curve family per product.

## Choreography

* Stagger to show relationship and order, with a small delay per item, and
  cap the total so the last item does not arrive after the user has started
  reading the first.
* Animate the parent or the child, not both in competing ways.
* When the same object persists across a state or route change, animate it
  to preserve continuity.
* Show content the user is waiting for without an entry animation.

## Scroll-linked motion

* Reveal-on-enter needs only an intersection observation or the platform's
  view-progress timeline; a scroll-orchestration library for simple reveals
  is over-tooling.
* Reveals fire once, not on every scroll back through a section.
* Pin a sequence when the section's top reaches the viewport top. Starting
  the animation before the pin shows half a frame of the intended
  composition.
* In a stacked-card sequence, every card except the last pins, and each
  card's recede transform is driven by the arrival of the next card, not by
  its own progress.
* In a horizontal pan, the wrapper pins and the inner track translates, with
  the scroll length set to the track's overflow width so the pan finishes
  exactly as the pin releases. Recompute on resize.
* Scroll hijacking removes control from the user. Budget at most one such
  section, and keep it off surfaces where the user has a task to complete.
* **Drive scroll-linked motion with scroll-driven timelines, an intersection
  observer, or frame-external animation values.** Raw scroll events and
  render state rerun work every frame and collapse on mid-range hardware.

## Restraint

* Infinite loops are for live state only. Ambient perpetual motion in the
  periphery competes for attention permanently and returns nothing.
* At most one attention-seeking device per view.
* Keep motion from blocking input: the user can always click through, scroll
  past, or skip.
* An animation must handle being reversed or restarted mid-flight without
  snapping.

## Reduced motion is a requirement

Honor the reduced-motion preference: replace movement with a fade or an
instant change, disable parallax and scroll hijacking entirely, stop
infinite loops, and keep every transition of state legible without the
animation.

Reduced motion means less movement, never less function. Never gate content,
state changes, or affordances behind an animation the preference disables.
Check the preference at the point of use so a change mid-session takes
effect.

Respect reduced-transparency and forced-colors preferences on the same
principle, with a solid, high-contrast fallback for any material effect.

## Performance

* Animate only compositor-friendly properties: transform and opacity.
  Animating geometry forces layout every frame.
* Promote only what animates; blanket promotion consumes memory and can
  degrade what it was meant to help.
* Keep grain, noise, and heavy filters on a fixed, non-interactive overlay
  layer; in a scrolling container they repaint continuously.
* Lazy-load animation libraries and heavy scenes not needed for the first
  view, and tear down every observer, timeline, and context on unmount.
