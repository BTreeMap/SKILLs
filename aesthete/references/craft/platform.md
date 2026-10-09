# Craft: platform

Reach for platform before dependency. Native capability arrives with
accessibility, keyboard behavior, top-layer rendering already correct; adds
no dependency code to bundle.

Browser support moves continuously; this file ages. Before relying on any
capability below, verify current baseline status against project's stated
support targets; provide graceful fallback when feature is progressive, not
essential.

## Choosing the layer

1. **Native element** whose semantics match: button, disclosure, dialog,
   label bound to its input, ordered list.
2. **Platform API** for behavior: top-layer overlays, transitions between
   states or documents, scroll-linked progress, anchored positioning.
3. **CSS** for anything visual or state-driven CSS can express.
4. **Dependency**, only when above cannot express it, only one per concern.
   Never install positioning, modal, or animation dependency for behavior
   platform provides natively.

Style native control; rebuild gains little styling and keeps accessibility
and keyboard issues. Custom control that does ship carries full keyboard and
assistive contract.

## Capabilities worth knowing

**Overlays and layering.** Real top-layer rendering for dialogs and
lightweight popovers, including backdrop styling, escape dismissal, focus
handling, light dismissal; plus anchored positioning tethering element to
reference without measurement code.

**Transitions.** Same-document and cross-document view transitions animate
between two states or two pages, including shared-element continuity,
without manual measurement. Entry animation for elements arriving in DOM and
animation of discrete properties both expressible in CSS.

**Scroll-linked animation.** Scroll progress and element-in-view progress
available as CSS timelines running off main thread. Prefer these over
observers for pure visual effects; observers over event listeners in every
case.

**Container context.** Size and style queries let component respond to own
container; container-relative units let type and spacing scale with context.

**Relational styling.** Parent-, sibling-, state-relational selectors
express in one rule what previously required state plumbing through
component tree.

**Color.** Perceptually uniform color spaces, color mixing, single
declarations selecting per theme let palette derive from few source values.

**Typography.** Line balancing for headings, orphan avoidance for body,
trimming of font-metric whitespace for exact optical spacing, control of
digit forms: all native.

**Form ergonomics.** Native validity states distinguish "invalid" from
"invalid after the user has interacted", preventing validation of half-typed
field. Fields can size to content. Platform styles selection colors and
control accents directly.

**Rendering and inertness.** Content can be marked inert for interaction and
assistive technology; offscreen content can be skipped during rendering for
large documents.

## Framework posture

Match repository. Choosing for greenfield work:

* Render as much as possible statically or on server; interactivity as
  isolated leaves. Never mark whole page interactive because one element is.
  Every interactive boundary adds client work for every user.
* Handle asynchronous state with framework's own mechanisms for pending
  state, optimistic updates, form submission; hand-rolled loading flags are
  where missing loading and error states come from.
* Stream what can be streamed: usable shell immediately beats nothing until
  everything resolves.
* Add animation library when interaction needs interruptible, physics-based,
  or gesture-driven motion. Platform reveals and transitions for simpler
  interactions.
* One animation system per component tree; two compete for same frames.

## Performance targets

One vendor's product thresholds, revisable by that vendor; never trade
criterion in `a11y` against one of them. Design constraints from start, not
post-launch audit; re-verify values when they matter.

* Largest contentful paint under 2.5 seconds. Hero image or heading
  prioritized, not blocked by font request or client bundle.
* Interaction to next paint under 200 milliseconds. Heavy work moves off
  main thread or gets chunked.
* Cumulative layout shift under 0.1. Everything asynchronous has reserved
  space; fonts metric-matched.

Budget bundle before writing it. Lazy-load anything below fold; weigh any
dependency against number of users incurring its cost every visit.
