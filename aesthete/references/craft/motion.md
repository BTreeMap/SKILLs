# Craft: motion

Motion exists to explain change. An animation that does not help the user
understand what happened, what is happening, or what to do next is a cost
charged to every user on every visit.

## The justification test

Before adding any animation, state in one sentence what it communicates. The
only valid answers:

* **Continuity**: this element is the same object that was over there.
* **Hierarchy**: look here first.
* **Causality**: this happened because you did that.
* **Progress**: work is underway and this is how much remains.
* **Narrative**: this sequence has an order the user should follow.

"It looked good" is not an answer. Motion added because the library was
available is the most common self-inflicted regression in generated
interfaces. If the sentence does not come, remove the animation.

## Duration and curve

* Small, local changes: fast enough to feel immediate rather than animated.
  Hover and press feedback belongs at the short end.
* Elements entering or leaving: moderate, and asymmetric. Exits run faster
  than entrances, because the user has already decided.
* Large surfaces crossing the screen: longer, but the ceiling is low.
  Anything past roughly half a second in a product interface starts costing
  the user time on every repetition.
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
* Entry animation on content the user is waiting for delays the content.
  Never animate in something that was already late.

## Scroll-linked motion

The mechanism matters more than the library.

* Reveal-on-enter is the common case and needs only an intersection
  observation or the platform's view-progress timeline. Reaching for a
  scroll-orchestration library for simple reveals is over-tooling.
* Reveals fire once. Re-animating on every scroll back through a section is
  a distraction the user did not ask for repeatedly.
* Pinned sequences pin at the moment the section's top reaches the viewport
  top, never partway. Starting the animation before the section is pinned is
  the characteristic failure and shows the user half a frame of the intended
  composition.
* In a stacked-card sequence, every card except the last pins, and each
  card's recede transform is driven by the arrival of the next card, not by
  its own progress.
* In a horizontal pan, the wrapper pins and the inner track translates, with
  the scroll length set to the track's overflow width so the pan finishes
  exactly as the pin releases. Recompute on resize.
* Scroll hijacking removes control from the user. Budget at most one such
  section, and never on a surface where the user has a task to complete.

**Never subscribe to raw scroll events and never drive continuous values
through render state.** Both re-run work every frame and collapse on
mid-range hardware. Use the platform's scroll-driven timelines, an
intersection observer, or the animation library's frame-external value
primitives.

## Restraint

* Infinite loops are for genuine live state only. Ambient perpetual motion
  in the periphery competes for attention permanently and never wins
  anything back.
* At most one attention-seeking device per view. Two things looping are two
  things being ignored.
* Motion never blocks input. The user can always click through, scroll past,
  or skip.
* Interruption is normal: an animation must handle being reversed or
  restarted mid-flight without snapping.

## Reduced motion is a requirement

Users request reduced motion for vestibular disorders, migraine, and
attention. Honor it: replace movement with a fade or an instant change,
disable parallax and scroll-hijacking entirely, stop infinite loops, and
keep every transition of state legible without the animation.

Reduced motion means less movement, not less function. Never gate content,
state changes, or affordances behind an animation that the preference
disables. Check the preference at the point of use so a change mid-session
takes effect.

Respect reduced transparency and forced-colors preferences on the same
principle, with a solid, high-contrast fallback for any material effect.

## Performance

* Animate only compositor-friendly properties: transform and opacity.
  Animating geometry forces layout every frame.
* Promote sparingly and only what actually animates; blanket promotion
  consumes memory and can degrade what it was meant to help.
* Grain, noise, and heavy filters belong on a fixed, non-interactive overlay
  layer, never on a scrolling container where they repaint continuously.
* Lazy-load animation libraries and heavy scenes that are not needed for the
  first view, and tear down every observer, timeline, and context on unmount.

## Completion checks

<validation_checklist>
  <item>Every animation passes the one-sentence justification test.</item>
  <item>Durations are short, exits faster than entrances, with one curve family across the product.</item>
  <item>Staggers are capped and nothing the user is waiting for is animated in.</item>
  <item>Shared-element continuity is used where an object genuinely persists.</item>
  <item>Scroll-linked sequences pin at the correct moment and reveals fire once.</item>
  <item>No raw scroll subscriptions and no continuous values in render state.</item>
  <item>Reduced motion, reduced transparency, and forced colors are honored without losing function.</item>
  <item>Only transform and opacity animate; heavy effects are isolated and torn down.</item>
</validation_checklist>
