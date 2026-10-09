# Verb: build

Takes request for new interface work (default verb for it); returns working
code. No design plan exists: first produce compressed one inline: primary
goal, token spine, composition order.

## Order of work

Build in this order; each stage constrains next; reordering causes rework.

1. **Inventory before authoring**, per `components`. List what exists and
   will be reused, what exists and needs new variant, what does not exist
   yet. Author only third category.
2. **Tokens before components.** Adopt supplied or existing token set, or
   define one where none exists: type scale, spacing scale, radius scale,
   color tokens for every theme, motion curves, elevation, as named values
   in one place. Verify adopted tokens against accessibility floor before
   building on them. Token for every component value where one exists or
   should exist.
3. **Layout before ornament.** Establish structural grid, container widths,
   responsive behavior. Hierarchy does not read as grayscale wireframe with
   all color and decoration removed: fix before adding styling.
4. **States before polish.** Implement every state `interaction` defines,
   for every interactive element and data container, before refining any
   visual detail.
5. **Content before motion.** Real copy, real or honestly labeled data, real
   or explicitly slotted imagery. Motion last, to page that already works
   without it.
6. **Verification.** Both themes, keyboard-only pass, reduced-motion pass,
   narrow viewport, `preflight`.

## Implementation rules

* **Compose with installed system.** Design system present: use its
  components and tokens. Overriding more than small fraction of its tokens
  means wrong system chosen; say so.
* **Isolate interactivity.** Interactive and animated pieces are leaf
  components with explicit client boundary; structural layout stays static
  and server-rendered where framework supports it.
* **Drive continuous values outside render state.** Pointer position, scroll
  progress, physics run outside render cycle through animation library's
  value primitives or CSS. Re-rendering tree per frame collapses on
  mid-range hardware.
* **Reserve space for everything asynchronous.** Images, fonts, embeds,
  late-loading regions carry explicit dimensions so nothing shifts.
* **One family per concern**: one icon set at one weight, one animation
  library per component tree, one styling strategy, one theming mechanism.
* **Semantics first.** Native element before composed one: real button,
  dialog, disclosure, label bound to its input. Custom control only when
  native one cannot express behavior; then implement full keyboard and
  assistive contract.
* **Clean up.** Tear down every subscription, observer, timer, animation
  context on unmount.

## Assets

Visual assets in this priority order: available image-generation capability,
producing section-specific assets at correct aspect ratio; then real
licensed or brand-supplied imagery; then seeded placeholder service with
descriptive seeds. None available: leave labeled slot naming required
dimensions and subject; name in response every asset interface still needs.
Never fill image slot with decorative gradients as stand-in for content.

## Output

Code first. Then at most short block: dials used, assets still required,
friction budget to primary goal, anything deliberately deferred. No feature
tour, no restatement of what code plainly does.

## Completion checks

<checklist>
  <item>Repository inventoried first; everything reusable reused; nothing forked silently.</item>
  <item>Tokens defined before components; no component hardcodes value belonging to scale.</item>
  <item>Variants and asynchronous states closed sets eliminated exhaustively; imports point downward; domain types at or above pattern layer.</item>
  <item>Hierarchy reads correctly with color and decoration removed.</item>
  <item>Every interactive element and data container ships every state `interaction` defines.</item>
  <item>Stack, library, tokens match repository; no undeclared dependency imported.</item>
  <item>Interactivity isolated to leaf components; continuous values bypass render state.</item>
  <item>Native semantic elements used wherever they suffice, full keyboard contracts on any custom control.</item>
  <item>Space reserved for every asynchronous element; effects torn down.</item>
  <item>Assets real, generated, or honestly slotted, never fabricated.</item>
  <item>Both themes, keyboard-only, reduced-motion, narrow viewport verified.</item>
</checklist>
