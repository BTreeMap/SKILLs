# Craft: platform

Reach for the platform before a dependency. Native capability arrives with
accessibility, keyboard behavior, and top-layer rendering already correct,
and adds no dependency code to the bundle.

Browser support moves continuously and this file ages. Before relying on any
capability below, verify its current baseline status against the project's
stated support targets, and provide a graceful fallback when the feature is
progressive rather than essential.

## Choosing the layer

1. **A native element** whose semantics match: the button, the disclosure,
   the dialog, the label bound to its input, the ordered list.
2. **A platform API** for behavior: top-layer overlays, transitions between
   states or documents, scroll-linked progress, anchored positioning.
3. **CSS** for anything visual or state-driven that CSS can express.
4. **A dependency**, only when the above cannot express it, and only one per
   concern. Never install a positioning, modal, or animation dependency for
   behavior the platform provides natively.

Style the native control; a rebuild gains little styling and keeps the
accessibility and keyboard issues. A custom control that does ship carries
its full keyboard and assistive contract.

## Capabilities worth knowing

**Overlays and layering.** Real top-layer rendering for dialogs and
lightweight popovers, including backdrop styling, escape dismissal, focus
handling, and light dismissal, plus anchored positioning that tethers an
element to a reference without measurement code.

**Transitions.** Same-document and cross-document view transitions animate
between two states or two pages, including shared-element continuity,
without manual measurement. Entry animation for elements arriving in the DOM
and animation of discrete properties are both expressible in CSS.

**Scroll-linked animation.** Scroll progress and element-in-view progress
are available as CSS timelines that run off the main thread. Prefer these
over observers for pure visual effects, and observers over event listeners
in every case.

**Container context.** Size and style queries let a component respond to its
own container, and container-relative units let type and spacing scale with
context.

**Relational styling.** Parent-, sibling-, and state-relational selectors
express in one rule what previously required state plumbing through the
component tree.

**Color.** Perceptually uniform color spaces, color mixing, and single
declarations that select per theme let a palette be derived from a few
source values.

**Typography.** Line balancing for headings, orphan avoidance for body,
trimming of font-metric whitespace for exact optical spacing, and control of
digit forms are all native.

**Form ergonomics.** Native validity states distinguish "invalid" from
"invalid after the user has interacted", which prevents validating a
half-typed field. Fields can size to their content. The platform styles
selection colors and control accents directly.

**Rendering and inertness.** Content can be marked inert for interaction and
assistive technology, and offscreen content can be skipped during rendering
for large documents.

## Framework posture

Match the repository. When choosing for greenfield work:

* Render as much as possible statically or on the server, and treat
  interactivity as isolated leaves; never mark a whole page interactive
  because one element in it is. Every interactive boundary adds client work
  for every user.
* Handle asynchronous state with the framework's own mechanisms for pending
  state, optimistic updates, and form submission; hand-rolled loading flags
  are where missing loading and error states come from.
* Stream what can be streamed: a usable shell immediately beats nothing
  until everything resolves.
* Add an animation library when the interaction needs interruptible,
  physics-based, or gesture-driven motion. Use platform reveals and
  transitions for simpler interactions.
* Use one animation system per component tree; two compete for the same
  frames.

## Performance targets

These are one vendor's product thresholds, revisable by that vendor; never
trade a criterion in `a11y` against one of them. Treat them as design
constraints from the start, not a post-launch audit, and re-verify the
values when they matter.

* Largest contentful paint under 2.5 seconds. The hero image or heading is
  prioritized and not blocked by a font request or a client bundle.
* Interaction to next paint under 200 milliseconds. Heavy work moves off the
  main thread or gets chunked.
* Cumulative layout shift under 0.1. Everything asynchronous has reserved
  space and fonts are metric-matched.

Budget the bundle before writing it. Lazy-load anything below the fold, and
weigh any dependency against the number of users who incur its cost on every
visit.
