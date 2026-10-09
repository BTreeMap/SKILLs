# Judging: sweeps, severity, and signs

## The five sweeps

1. **Logic**: behavior follows from appearance? state complete? errors
   preventable? work preserved? keyboard path exists?
2. **Hierarchy**: eye lands on right thing first? grayscale still reads?
   contrast spent on what matters?
3. **Consistency**: one accent, one radius scale, one spacing scale, one
   type scale, one icon family, one theme, across whole surface?
4. **Voice**: copy says what happened and what to do next? anything
   fabricated? anything reads as generated?
5. **Structure**: re-implements something repository already has? prop APIs
   admit invalid combinations? closed set handled with catch-all? imports
   point downward? effect synchronizes derivable state?

## Severity

Rate each finding on this scale.

| Level | Meaning |
| --- | --- |
| Broken | User cannot complete goal, loses work, or is excluded. Blocking. |
| Friction | Goal reachable but costs unjustified steps, waits, or confusion. |
| Incoherent | Violates surface's own established system. Cheap to fix, compounds if not. |
| Generated | Reads as templated output. Undermines credibility without breaking function. |

## Signs

Sign: pattern far more common in generated interfaces than considered ones;
design decision nobody made. Each banned as **default reach**; any is
available when brief calls for it and you can say why. Spine owns em-dash
and fabrication rules; not restated here.

Writing: derive each decision from design read; these patterns substitute
for decisions, so most disappear when each choice has reason. Examining:
count mechanically wherever count defined: section labels against section
count, consecutive split layouts, marquees, occurrences of U+2014, distinct
accent colors, distinct radius values.

### Typography

* **Word in different family dropped into heading** for visual interest.
  Emphasis stays within one family, using weight or italic.
* **Headings hard-broken and part-italicized** to force shape that survives
  one viewport and breaks in rest.
* **Vertically rotated labels** running up side of section.
* **Oversized display type substituting for hierarchy**, scale the only
  signal, everything else undifferentiated.

### Micro-labels and enumeration

* **Small uppercase wide-tracked label above every section heading.** Once
  or twice per page it orients; above every section it is clearest
  structural signature of generated layout. At most one per three sections.
* **Numbered section labels**: index numbers, zero-padded counts, or
  "phase", "stage", "step" prefixes on content already in order. Content is
  label.
* **Pagination counters on images or grid cells** when user can already see
  how many there are.
* **Generic step naming** in process section. Use each step's actual verb.
* **Decorative version and status stamps**: version number, release-stage
  badge, or access-tier label in heading area, on surface not about release.
* **Build metadata in footer** on surface that is not developer tooling.

### Separators and decoration

* **Middle dot as universal separator**, chaining several fragments into one
  metadata line. At most one per line; prefer columns, line breaks, or
  hairline.
* **Colored status dots before list items, navigation entries, badges**
  where nothing has status. Dot means live state or nothing.
* **Hairline grid lines and crosshairs drawn purely as ornament**,
  organizing no content.
* **Small caps strip across bottom of hero** listing capability words:
  decorative fragment pretending to be navigation.
* **Ambient location, time, or weather strips**, justified only for
  place-specific or timezone-distributed subject. Contact address in footer
  is not this.
* **Scroll prompts.** User looking at top of page knows pages scroll.

### Placeholder credibility

Honesty failures: fix ahead of any taste issue.

* **Placeholder people**: generic names, obviously synthetic avatars,
  round-numbered statistics.
* **Placeholder brands**: standard set of invented company names appearing
  across every generated example.
* **Credibility logo rows rendered as styled text names.** Use real vector
  marks, or simple generated monogram for invented brand.
* **Category labels beneath credibility logos.** Mark is credibility; label
  adds nothing reader does not already know.
* **Decorative photo credits and archival captions** under placeholder
  imagery. Credit real photographer for real photograph, write plain
  functional caption, or write none.
* **Live-sounding counters** implying real-time scarcity or activity that is
  not real.

### Copy

* **Filler verbs** meaning nothing in context: elevate, unleash, seamless,
  revolutionize, next-generation, effortless.
* **Performed modesty**: quietly-in-use-at, honest-by-design, similar
  constructions claiming virtue.
* **Craftsman-poetic section labels** on ordinary content: field notes, from
  the bench, loose ends. Use plain functional label or none.
* **Micro-explanations under headings** editorializing about section's own
  restraint or intentions.
* **Cute wordplay that does not survive literal reading.** Clever but
  slightly wrong is wrong. Plain and correct wins.
* **Mixed registers** in one composition: technical shorthand, editorial
  prose, marketing punch together with no editorial voice.
* **Duplicate calls to action with different labels** for same intent across
  one surface. One intent, one label, everywhere.
* **Call-to-action labels wrapping to two lines** at desktop. Shorten label
  or widen control.

### Composition

* **Three identical cards in a row** as reflexive way to present any set of
  three things.
* **Centered heading over dark mesh gradient** as reflexive hero.
* **Third consecutive alternating image-and-text row.**
* **Large heading with small paragraph floating in top-right corner** of
  same section header: unresolved alignment presented as composition.
* **Grid cells all text on uniform background.** Grid needs real visual
  variation or it is list.
* **Empty trailing grid cell**: grid shape chosen before content counted.
* **Every row of long list separated by hairline.** Group instead, or change
  component.
* **Filled progress tracks used as comparison graphics** on marketing
  surface.
* **Section inverting page theme** without being composed, deliberate
  device.

### Color and material

* **Purple-to-blue technology gradient** as unbriefed default; glow effects
  generally.
* **Warm-cream-with-brass palette** appearing on every artisan, wellness,
  cookware, premium consumer brief. Representative of family: backgrounds
  near `#f5f1ea`, `#faf7f1`, or `#efeae0`; accents near `#b08947`,
  `#b6553a`, or `#9a2436`; text near `#1a1714`. Palette is competent, which
  is why it recurs, and makes every brand using it invisible. Rotate to
  different family; never ship it twice in category.
* **Pure black or pure white** for large surfaces.
* **Translucent material applied to everything** instead of to one layer
  where depth carries meaning.
* **Custom cursors.** Slow, inaccessible, dated.
