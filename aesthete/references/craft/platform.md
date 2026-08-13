# Craft: platform

Reach for the platform before a dependency. Native capability arrives with
accessibility, keyboard behavior, and top-layer rendering already correct,
and costs nothing to ship.

**This file names capabilities, not a support matrix.** Browser support
moves continuously and this file ages. Before relying on any capability
below, verify its current baseline status and the project's stated support
targets, and provide a graceful fallback when the feature is progressive
rather than essential. Never assume, and never let this file substitute for
checking.

## Choosing the layer

1. **A native element** whose semantics match: the button, the disclosure,
   the dialog, the label bound to its input, the ordered list. Free
   correctness.
2. **A platform API** for behavior: top-layer overlays, transitions between
   states or documents, scroll-linked progress, anchored positioning.
3. **CSS** for anything visual or state-driven that CSS can express.
4. **A dependency**, only when the above genuinely cannot express it, and
   only one per concern.

Rebuilding a native control in order to style it is nearly always the wrong
trade: the styling gain is small and the accessibility and keyboard debt is
large and permanent.

## Capabilities worth knowing

**Overlays and layering.** The platform provides real top-layer rendering
for dialogs and lightweight popovers, including backdrop styling, escape
dismissal, focus handling, and light dismissal. It also provides anchored
positioning that tethers an element to a reference without measurement code.
Together these remove the most common reasons projects install a positioning
or modal dependency.

**Transitions.** Same-document and cross-document view transitions animate
between two states or two pages, including shared-element continuity,
without manual measurement. Entry animation for elements arriving in the DOM
and animation of discrete properties are both expressible in CSS.

**Scroll-linked animation.** Scroll progress and element-in-view progress
are available as CSS timelines that run off the main thread. Prefer these
over observers for pure visual effects, and observers over event listeners
in every case.

**Responsive to context, not viewport.** Size and style queries let a
component respond to its own container rather than the window, so one
component works in a sidebar, a modal, and a full-width region without
breakpoint duplication. Relative units tied to the container let type and
spacing scale with context.

**Selection and relational styling.** Parent-, sibling-, and
state-relational selectors express in one rule what previously required
state plumbing through the component tree.

**Color.** Perceptually uniform color spaces, color mixing, and single
declarations that select per theme let a palette be derived from a small
number of source values rather than hand-maintained per theme.

**Typography.** Line balancing for headings, orphan avoidance for body,
trimming of font-metric whitespace for exact optical spacing, and control of
digit forms are all native.

**Form ergonomics.** Native validity states distinguish "invalid" from
"invalid after the user has interacted", which is exactly the distinction
that prevents validating a half-typed field. Fields can size to their
content. The platform styles selection colors and control accents directly.

**Rendering and inertness.** Content can be marked inert for interaction and
assistive technology, and offscreen content can be skipped during rendering
for large documents.

## Framework posture

Match the repository. When choosing for greenfield work:

* Render as much as possible statically or on the server, and treat
  interactivity as isolated leaves. Every interactive boundary is a cost paid
  by every user.
* Handle asynchronous state with the framework's own mechanisms for pending
  state, optimistic updates, and form submission rather than hand-rolled
  loading flags. Hand-rolled flags are where the missing loading and error
  states come from.
* Stream what can be streamed. Showing a usable shell immediately beats
  showing nothing until everything resolves.
* Add an animation library when the interaction genuinely needs
  interruptible, physics-based, or gesture-driven motion. Simple reveals and
  transitions no longer justify one.
* Never mix two animation systems in one component tree; they compete for
  the same frames.

## Performance targets

Treat these as design constraints, not a post-launch audit.

* Largest contentful paint under 2.5 seconds. The hero image or heading is
  prioritized and not blocked by a font request or a client bundle.
* Interaction to next paint under 200 milliseconds. Heavy work moves off the
  main thread or gets chunked.
* Cumulative layout shift under 0.1. Everything asynchronous has reserved
  space and fonts are metric-matched.

Budget the bundle before writing it. Lazy-load anything below the fold, and
weigh any dependency against the number of users who pay for it on every
visit.

## Failure modes

* Installing a positioning, modal, or animation dependency for behavior the
  platform now provides natively.
* Using a capability without verifying support against the project's stated
  targets, and without a fallback.
* Building a custom control to get custom styling, then shipping it without
  its keyboard and assistive contract.
* Marking a whole page as interactive because one element in it is.
* Treating performance targets as something to measure after design rather
  than as constraints on design.

## Completion checks

<validation_checklist>
  <item>Current support status was verified for every capability relied on, against the project's stated targets.</item>
  <item>Native elements and platform APIs were exhausted before adding a dependency.</item>
  <item>No custom control replaces a native one without a full keyboard and assistive contract.</item>
  <item>Interactivity is isolated to leaves and asynchronous state uses framework mechanisms rather than hand-rolled flags.</item>
  <item>One animation system per component tree.</item>
  <item>Paint, interaction, and layout-stability targets were treated as design constraints and space is reserved for async content.</item>
  <item>Every dependency added is justified against the cost paid by every user.</item>
</validation_checklist>
