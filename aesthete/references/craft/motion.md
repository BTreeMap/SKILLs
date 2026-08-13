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

Use a communication purpose, not visual appeal, to justify motion. Use an
animation library only when it supplies a needed capability. If the sentence
does not come, remove the animation.

## Duration and curve

* Small, local changes: fast enough to feel immediate rather than animated.
  Hover and press feedback belongs at the short end.
* Elements entering or leaving: moderate, and asymmetric. Exits run faster
  than entrances, because the user has already decided.
* Large surfaces crossing the screen: longer, but keep them brief. Anything
  past roughly half a second in a product interface starts costing the user
  time on every repetition.
* Distance scales duration, but sublinearly. A larger object crossing a
  larger distance takes somewhat longer, not proportionally longer.
* Use eased curves that decelerate into rest. Linear motion reads mechanical
  except for continuous ambient movement and progress indicators. Spring
  behavior suits direct manipulation, where the user's gesture should feel
  physically connected.
* One curve family per product. Mixed easing across components is as
  incoherent as mixed radii.

## Choreography

* Stagger to show relationship and order, with a small delay per item, and
  cap the total: a long stagger across many items means the last item
  arrives after the user has already started reading the first.
* Animate the parent or the child, not both in competing ways.
* Shared-element continuity is the highest-value motion available: when the
  same object persists across a state or route change, animate it rather
  than crossfading two representations. This is the one case where motion
  genuinely reduces cognitive load rather than merely decorating.
* Show content the user is waiting for without an entry animation.

## Scroll-linked motion

The mechanism matters more than the library.

* Reveal-on-enter is the common case and needs only an intersection
  observation or the platform's view-progress timeline. Reaching for a
  scroll-orchestration library for simple reveals is over-tooling.
* Reveals fire once. Re-animating on every scroll back through a section is
  a distraction the user did not ask for repeatedly.
* Pin sequences when the section's top reaches the viewport top. Starting the
  animation before the section is pinned shows the user half a frame of the
  intended composition.
* In a stacked-card sequence, every card except the last pins, and each
  card's recede transform is driven by the arrival of the next card, not by
  its own progress.
* In a horizontal pan, the wrapper pins and the inner track translates, with
  the scroll length set to the track's overflow width so the pan finishes
  exactly as the pin releases. Recompute on resize.
* Scroll hijacking removes control from the user. Budget at most one such
  section, and keep it off surfaces where the user has a task to complete.

**Use scroll-driven timelines, an intersection observer, or frame-external
animation values.** Raw scroll events and render state rerun work every frame
and collapse on mid-range hardware.

## Restraint

* Infinite loops are for genuine live state only. Ambient perpetual motion
  in the periphery competes for attention permanently and does not return
  anything to the user.
* At most one attention-seeking device per view. Two things looping are two
  things being ignored.
* Keep motion from blocking input. The user can always click through, scroll
  past, or skip.
* Interruption is normal: an animation must handle being reversed or
  restarted mid-flight without snapping.

## Reduced motion is a requirement

Users request reduced motion for vestibular disorders, migraine, and
attention. Honor it: replace movement with a fade or an instant change,
disable parallax and scroll-hijacking entirely, stop infinite loops, and
keep every transition of state legible without the animation.

Reduced motion means less movement. It does not reduce function. Never gate
content, state changes, or affordances behind an animation that the preference
disables. Check the preference at the point of use so a change mid-session
takes effect.

Respect reduced transparency and forced-colors preferences on the same
principle, with a solid, high-contrast fallback for any material effect.

## Performance

* Animate only compositor-friendly properties: transform and opacity.
  Animating geometry forces layout every frame.
* Promote sparingly and only what actually animates; blanket promotion
  consumes memory and can degrade what it was meant to help.
* Keep grain, noise, and heavy filters on a fixed, non-interactive overlay
  layer instead of a scrolling container where they repaint continuously.
* Lazy-load animation libraries and heavy scenes that are not needed for the
  first view, and tear down every observer, timeline, and context on unmount.
