# Verb: build

Implement an interface. Default verb for new work.

## Preconditions

The design read and dials are stated. If no design plan exists, produce a
compressed one inline (primary goal, token spine, composition order) before
writing components.

## Order of work

Build in this order. Each stage constrains the next, and reordering causes
rework.

1. **Inventory before authoring.** Search the repository for every component,
   variant, hook, and token the screen needs before writing anything. List
   what exists and will be reused, what exists and needs a new variant, and
   what genuinely does not exist yet. Only the third category gets authored.
   Inventory first so existing components are reused and the codebase does
   not acquire its third Button.
2. **Tokens before components.** Adopt the supplied or existing token set,
   or define one where none exists: type scale, spacing scale, radius scale,
   color tokens for every theme, motion curves, elevation, as named values
   in one place. Verify adopted tokens against the accessibility floor
   before building on them. Use tokens for component values whenever a token
   exists or should exist.
3. **Layout before ornament.** Establish the structural grid, the container
   widths, and the responsive behavior. Verify the hierarchy reads with all
   color and decoration removed. If it does not read in grayscale wireframe,
   fix the hierarchy before adding styling.
4. **States before polish.** Implement every state `interaction`
   defines, for every interactive element and every data container, before
   refining any visual detail. Model each as one closed set so that omitting
   a state fails the build.
5. **Content before motion.** Real copy, real or honestly-labeled data, real
   or explicitly-slotted imagery. Motion is applied last, to a page that
   already works without it.
6. **Verification.** Both themes, keyboard-only pass, reduced-motion pass,
   narrow viewport, and the mechanical gate.

## Implementation rules

* **Derive the stack.** Match the repository's framework, styling approach,
  component library, and conventions. Confirm every dependency exists before
  importing it; if absent, state the install command first.
* **Compose with the installed system.** When a design system is present,
  use its components and tokens. Overriding more than a small fraction of a
  system's tokens means the wrong system was chosen; say so rather than
  fighting it component by component.
* **Isolate interactivity.** Interactive and animated pieces are leaf
  components with an explicit client boundary; structural layout stays
  static and server-rendered where the framework supports it.
* **Drive continuous values outside render state.** Pointer position, scroll
  progress, and physics run outside the render cycle through the animation
  library's value primitives or CSS. Re-rendering a tree per frame collapses
  on mid-range hardware.
* **Reserve space for everything asynchronous.** Images, fonts, embeds, and
  late-loading regions carry explicit dimensions so nothing shifts.
* **One family per concern.** One icon set at one weight, one animation
  library per component tree, one styling strategy, one theming mechanism.
* **One component per concept.** Extend an existing component with a variant
  rather than copying it. If a copy is genuinely the honest answer, explain
  the reason before creating it.
* **Close the variant sets.** Model variants and asynchronous states as one
  closed set eliminated exhaustively, not as independent booleans with a
  catch-all branch. Keep imports pointing downward through the layer ladder
  `components` defines, with domain types no lower than the pattern
  layer.
* **Semantics first.** Use the native element before the composed one: a
  real button, a real dialog, a real disclosure, a real label bound to its
  input. Reach for a custom control only when the native one genuinely
  cannot express the behavior, and then implement its full keyboard and
  assistive contract.
* **Clean up.** Every subscription, observer, timer, and animation context
  is torn down on unmount.

## Honest asset handling

Priority order for visual assets: an available image-generation capability
first, producing section-specific assets at the correct aspect ratio; then
real licensed or brand-supplied imagery; then a seeded placeholder service
with descriptive seeds. If none is available, leave a labeled slot naming
the required dimensions and subject, and state in the response which assets
the interface still needs. Never substitute a fabricated interface built
from styled containers, and never fill an image slot with decorative
gradients as a stand-in for content.

## Output

Code first. Then at most a short block covering: the dials used, assets
still required, the friction budget to the primary goal, and anything
deliberately deferred. No feature tour, no restatement of what the code
plainly does.

## Completion checks

<validation_checklist>
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
</validation_checklist>
