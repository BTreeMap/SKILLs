# Verb: build

Takes a request for new interface work (the default verb for it) and returns
working code. If no design plan exists, first produce a compressed one
inline: primary goal, token spine, composition order.

## Order of work

Build in this order; each stage constrains the next, and reordering causes
rework.

1. **Inventory before authoring**, per `components`. List what exists and
   will be reused, what exists and needs a new variant, and what does not
   exist yet. Author only the third category.
2. **Tokens before components.** Adopt the supplied or existing token set,
   or define one where none exists: type scale, spacing scale, radius scale,
   color tokens for every theme, motion curves, and elevation, as named
   values in one place. Verify adopted tokens against the accessibility
   floor before building on them. Use a token for every component value
   where one exists or should exist.
3. **Layout before ornament.** Establish the structural grid, the container
   widths, and the responsive behavior. If the hierarchy does not read as a
   grayscale wireframe with all color and decoration removed, fix it before
   adding styling.
4. **States before polish.** Implement every state `interaction` defines,
   for every interactive element and data container, before refining any
   visual detail.
5. **Content before motion.** Real copy, real or honestly labeled data, real
   or explicitly slotted imagery. Apply motion last, to a page that already
   works without it.
6. **Verification.** Both themes, a keyboard-only pass, a reduced-motion
   pass, the narrow viewport, and `preflight`.

## Implementation rules

* **Compose with the installed system.** When a design system is present,
  use its components and tokens. Overriding more than a small fraction of
  its tokens means the wrong system was chosen; say so.
* **Isolate interactivity.** Interactive and animated pieces are leaf
  components with an explicit client boundary; structural layout stays
  static and server-rendered where the framework supports it.
* **Drive continuous values outside render state.** Pointer position, scroll
  progress, and physics run outside the render cycle through the animation
  library's value primitives or CSS. Re-rendering a tree per frame collapses
  on mid-range hardware.
* **Reserve space for everything asynchronous.** Images, fonts, embeds, and
  late-loading regions carry explicit dimensions so nothing shifts.
* **One family per concern**: one icon set at one weight, one animation
  library per component tree, one styling strategy, one theming mechanism.
* **Semantics first.** Use the native element before the composed one: a
  real button, dialog, disclosure, and label bound to its input. Reach for a
  custom control only when the native one cannot express the behavior, and
  then implement its full keyboard and assistive contract.
* **Clean up.** Tear down every subscription, observer, timer, and animation
  context on unmount.

## Assets

Take visual assets in this priority order: an available image-generation
capability, producing section-specific assets at the correct aspect ratio;
then real licensed or brand-supplied imagery; then a seeded placeholder
service with descriptive seeds. If none is available, leave a labeled slot
naming the required dimensions and subject, and name in the response every
asset the interface still needs. Never fill an image slot with decorative
gradients as a stand-in for content.

## Output

Code first. Then at most a short block covering the dials used, assets still
required, the friction budget to the primary goal, and anything deliberately
deferred. No feature tour, no restatement of what the code plainly does.

## Completion checks

<checklist>
  <item>The repository was inventoried first; everything reusable was reused and nothing was forked silently.</item>
  <item>Tokens were defined before components and no component hardcodes a value that belongs to a scale.</item>
  <item>Variants and asynchronous states are closed sets eliminated exhaustively; imports point downward and domain types stay at or above the pattern layer.</item>
  <item>Hierarchy reads correctly with color and decoration removed.</item>
  <item>Every interactive element and data container ships every state `interaction` defines.</item>
  <item>Stack, library, and tokens match the repository; no undeclared dependency is imported.</item>
  <item>Interactivity is isolated to leaf components and continuous values bypass render state.</item>
  <item>Native semantic elements were used wherever they suffice, with full keyboard contracts on any custom control.</item>
  <item>Space is reserved for every asynchronous element and effects are torn down.</item>
  <item>Assets are real, generated, or honestly slotted, never fabricated.</item>
  <item>Both themes, keyboard-only, reduced-motion, and narrow viewport were verified.</item>
</checklist>
