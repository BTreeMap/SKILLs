# Tells: the catalogue of generated-looking output

A tell is a pattern that appears far more often in generated interfaces than
in considered ones, a design decision nobody made, and readers who
see many interfaces recognize each instantly. Each is banned as a **default
reach**. Any of these is available when the brief genuinely calls for it and
you can say why.

## Typography and punctuation

* **The em-dash character, U+2014, anywhere a user can see it.** Headings,
  labels, buttons, body copy, quotes, attribution, captions, alternative
  text, empty states, error messages. The single highest-signal marker of
  generated text. Replace with a period, a comma, a colon, parentheses, or a
  restructured sentence. The en-dash U+2013 is likewise banned as a
  separator; ranges take a plain hyphen.
* **A word in a different family dropped into a heading** for visual
  interest. Emphasis stays within one family, using weight or italic.
* **Headings hard-broken and part-italicized** to force a shape. The shape
  survives one viewport and breaks in the rest.
* **Vertically rotated labels** running up the side of a section.
* **Oversized display type substituting for hierarchy**, where scale is the
  only signal and everything else is undifferentiated.

## Micro-labels and enumeration

* **A small uppercase wide-tracked label above every section heading.** Once
  or twice per page it orients; above every section it is the clearest
  structural signature of generated layout. At most one per three sections.
* **Numbered section labels**: index numbers, zero-padded counts, or
  "phase", "stage", and "step" prefixes attached to content that is already
  in order. The content is the label.
* **Pagination counters on images or grid cells** when the user can already
  see how many there are.
* **Generic step naming** in a process section. Use the actual verb of each
  step.
* **Version and status stamps** used decoratively: a version number, a
  release-stage badge, or an access-tier label in a heading area, on a
  surface that is not about a release.
* **Build metadata in a footer** on a surface that is not developer tooling.

## Separators and decoration

* **The middle dot used as the universal separator**, chaining several
  fragments into one metadata line. At most one per line; prefer columns,
  line breaks, or a hairline.
* **Colored status dots before list items, navigation entries, and badges**
  where nothing has a status. A dot means live state or it means nothing.
* **Hairline grid lines and crosshairs drawn purely as ornament**, not
  organizing any content.
* **A small caps strip across the bottom of a hero** listing capability
  words. It is a decorative fragment pretending to be navigation.
* **Ambient location, time, or weather strips.** Justified only for a
  genuinely place-specific or timezone-distributed subject. A contact
  address in a footer is not this.
* **Scroll prompts.** A user looking at the top of a page knows that pages
  scroll.

## Fabrication

Treat these as honesty failures and fix them ahead of any taste issue.

* **An interface built from styled containers standing in for a product
  screenshot**: an invented task list, dashboard, chart, or terminal
  assembled from primitives. The most recognizable single tell in generated
  marketing pages. Use a real capture, a generated image, a genuinely
  embedded component, or no preview.
* **Invented precision**: percentages, multipliers, measurements, and
  weights implying measurement nobody performed. Real, explicitly labeled
  as illustrative, or absent.
* **Placeholder people**: generic names, obviously synthetic avatars, and
  round-numbered statistics.
* **Placeholder brands**: the standard set of invented company names that
  appear across every generated example.
* **Credibility logo rows rendered as styled text names.** Use real vector
  marks, or a simple generated monogram for an invented brand.
* **Category labels beneath credibility logos.** The mark is the
  credibility; the label adds nothing the reader does not already know.
* **Decorative photo credits and archival captions** under placeholder
  imagery. Credit a real photographer for a real photograph, or write a
  plain functional caption, or none.
* **Live-sounding counters** implying real-time scarcity or activity that is
  not real.

## Copy

* **Filler verbs** that mean nothing in context: elevate, unleash,
  seamless, revolutionize, next-generation, effortless.
* **Performed modesty**: quietly-in-use-at, honest-by-design, and similar
  constructions that claim a virtue.
* **Craftsman-poetic section labels** on ordinary content: field notes, from
  the bench, loose ends. Use the plain functional label or none.
* **Micro-explanations under headings** editorializing about the section's
  own restraint or intentions.
* **Cute wordplay that does not survive a literal reading.** If a phrase is
  clever but slightly wrong, it is wrong. Plain and correct wins.
* **Mixed registers** in one composition: technical shorthand, editorial
  prose, and marketing punch together with no editorial voice.
* **Duplicate calls to action with different labels** for the same intent
  across one surface. One intent, one label, everywhere.
* **Call-to-action labels that wrap to two lines** at desktop. Shorten the
  label or widen the control.

## Composition

* **Three identical cards in a row** as the reflexive way to present any set
  of three things.
* **A centered heading over a dark mesh gradient** as the reflexive hero.
* **A third consecutive alternating image-and-text row.**
* **A large heading with a small paragraph floating in the top-right
  corner** of the same section header. Unresolved alignment presented as
  composition.
* **Grid cells that are all text on a uniform background.** A grid needs
  real visual variation or it is a list.
* **An empty trailing grid cell**, which means the grid shape was chosen
  before the content was counted.
* **Every row of a long list separated by a hairline.** Group instead, or
  change the component.
* **Filled progress tracks used as comparison graphics** on a marketing
  surface.
* **A section that inverts the page theme** without being a composed,
  deliberate device.

## Color and material

* **The purple-to-blue technology gradient** as an unbriefed default, and
  glow effects generally.
* **The warm-cream-with-brass palette** that appears on every artisan,
  wellness, cookware, and premium consumer brief. Representative of the
  family: backgrounds near `#f5f1ea`, `#faf7f1`, or `#efeae0`; accents near
  `#b08947`, `#b6553a`, or `#9a2436`; text near `#1a1714`. The palette is
  competent, which is why it recurs, and it makes every brand using it
  invisible. Rotate to a different family, and never ship it twice in a
  category.
* **Pure black or pure white** for large surfaces.
* **Translucent material applied to everything** rather than to the one
  layer where depth carries meaning.
* **Custom cursors.** Slow, inaccessible, and dated.
* **A second accent color** introduced in a later section.

## Using this file

When reviewing, count mechanically wherever a count is defined: section
labels against section count, consecutive split layouts, marquees,
occurrences of U+2014, distinct accent colors, distinct radius values. A
count is not an opinion.

When building, derive each decision from the design read. These patterns
substitute for decisions, so most disappear when each choice has a reason.
