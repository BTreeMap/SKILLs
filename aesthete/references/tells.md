# Judging: sweeps, severity, and tells

## The five sweeps

1. **Logic**: does behavior follow from appearance, is state complete, are
   errors preventable, is work preserved, does the keyboard path exist?
2. **Hierarchy**: does the eye land on the right thing first, does grayscale
   still read, is contrast spent on what matters?
3. **Consistency**: one accent, one radius scale, one spacing scale, one
   type scale, one icon family, one theme, across the whole surface?
4. **Voice**: does the copy say what happened and what to do next, is
   anything fabricated, does anything read as generated?
5. **Structure**: does this re-implement something the repository already
   has, do prop APIs admit invalid combinations, is any closed set handled
   with a catch-all, do imports point downward, does an effect synchronize
   derivable state?

## Severity

Rate each finding on this scale.

| Level | Meaning |
| --- | --- |
| Broken | The user cannot complete the goal, loses work, or is excluded. Blocking. |
| Friction | The goal is reachable but costs unjustified steps, waits, or confusion. |
| Incoherent | Violates the surface's own established system. Cheap to fix, compounds if not. |
| Generated | Reads as templated output. Undermines credibility without breaking function. |

## Tells

A tell is a pattern far more common in generated interfaces than in
considered ones: a design decision nobody made. Each is banned as a
**default reach**; any of them is available when the brief calls for it and
you can say why. The spine owns the em-dash and fabrication rules; this file
does not restate them.

When building, derive each decision from the design read; these patterns
substitute for decisions, so most disappear when each choice has a reason.
When reviewing, count mechanically wherever a count is defined: section
labels against section count, consecutive split layouts, marquees,
occurrences of U+2014, distinct accent colors, distinct radius values.

### Typography

* **A word in a different family dropped into a heading** for visual
  interest. Emphasis stays within one family, using weight or italic.
* **Headings hard-broken and part-italicized** to force a shape that
  survives one viewport and breaks in the rest.
* **Vertically rotated labels** running up the side of a section.
* **Oversized display type substituting for hierarchy**, where scale is the
  only signal and everything else is undifferentiated.

### Micro-labels and enumeration

* **A small uppercase wide-tracked label above every section heading.** Once
  or twice per page it orients; above every section it is the clearest
  structural signature of generated layout. At most one per three sections.
* **Numbered section labels**: index numbers, zero-padded counts, or
  "phase", "stage", and "step" prefixes on content already in order. The
  content is the label.
* **Pagination counters on images or grid cells** when the user can already
  see how many there are.
* **Generic step naming** in a process section. Use each step's actual verb.
* **Decorative version and status stamps**: a version number, a
  release-stage badge, or an access-tier label in a heading area, on a
  surface that is not about a release.
* **Build metadata in a footer** on a surface that is not developer tooling.

### Separators and decoration

* **The middle dot as the universal separator**, chaining several fragments
  into one metadata line. At most one per line; prefer columns, line breaks,
  or a hairline.
* **Colored status dots before list items, navigation entries, and badges**
  where nothing has a status. A dot means live state or nothing.
* **Hairline grid lines and crosshairs drawn purely as ornament**,
  organizing no content.
* **A small caps strip across the bottom of a hero** listing capability
  words: a decorative fragment pretending to be navigation.
* **Ambient location, time, or weather strips**, justified only for a
  place-specific or timezone-distributed subject. A contact address in a
  footer is not this.
* **Scroll prompts.** A user looking at the top of a page knows that pages
  scroll.

### Placeholder credibility

Treat these as honesty failures and fix them ahead of any taste issue.

* **Placeholder people**: generic names, obviously synthetic avatars, and
  round-numbered statistics.
* **Placeholder brands**: the standard set of invented company names that
  appear across every generated example.
* **Credibility logo rows rendered as styled text names.** Use real vector
  marks, or a simple generated monogram for an invented brand.
* **Category labels beneath credibility logos.** The mark is the
  credibility; the label adds nothing the reader does not already know.
* **Decorative photo credits and archival captions** under placeholder
  imagery. Credit a real photographer for a real photograph, write a plain
  functional caption, or write none.
* **Live-sounding counters** implying real-time scarcity or activity that is
  not real.

### Copy

* **Filler verbs** that mean nothing in context: elevate, unleash, seamless,
  revolutionize, next-generation, effortless.
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

### Composition

* **Three identical cards in a row** as the reflexive way to present any set
  of three things.
* **A centered heading over a dark mesh gradient** as the reflexive hero.
* **A third consecutive alternating image-and-text row.**
* **A large heading with a small paragraph floating in the top-right
  corner** of the same section header: unresolved alignment presented as
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

### Color and material

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
