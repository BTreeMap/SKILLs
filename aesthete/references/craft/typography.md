# Craft: typography

Get type right before touching color.

## The scale

Fix one scale and use only its steps; six to eight steps covers almost every
interface. Keep adjacent steps perceptibly distinct: many near-identical
steps produce hierarchy nobody can perceive and inconsistency everybody can.
A ratio near 1.2 suits dense product interfaces; near 1.333 suits marketing
surfaces where display type does expressive work.

Set the scale in a relative unit so it honors the user's browser text size;
fixed pixel sizing for body text overrides an explicit accessibility
preference.

Size display type against the headline actually written, not one imagined: a
size chosen first wraps the real headline to four lines and breaks the
composition.

## Measure and rhythm

* Body measure between roughly 45 and 75 characters. Wider loses the line
  return; narrower fragments phrases.
* Line height inverse to size: generous for body text, tightening as display
  size grows, near or slightly above 1 only at the largest display sizes.
* Line height and spacing scale should share a rhythm so text blocks align
  to the same grid as everything else.
* Paragraph spacing separates; first-line indentation is for continuous
  prose. Use exactly one of the two.
* Tighten letter spacing slightly as size increases; loosen it only for
  uppercase and small text.

## Choosing faces

Two families is the working maximum: one for text, one for display or
monospace. Three requires a reason you can state. A pair must be distinct
enough to read as a pairing or close enough to read as one voice, never in
between.

Choose for the job. A face for an operator console needs unambiguous digits,
distinguishable I/l/1 and O/0, and a true monospace companion for numbers
and identifiers. A face for an editorial surface needs a real italic and
sufficient weight range. Verify the family ships the weights and the true
italic being used before designing around them. Where the weights are close
together, do not use weight as the only hierarchy signal.

**Serif discipline.** Reaching for a serif because it feels premium,
creative, or considered is the most common type misjudgment in generated
design. Use a serif when the surface is editorial, literary, or heritage, or
when the brand specifies one, and state why that serif suits that brand.
Otherwise choose a display sans, the common default in contemporary brand
work.

**Emphasis stays in the family.** Emphasize a word inside a heading with the
weight or the italic of the same family.

**Rotate faces.** Reusing the same two or three fashionable faces across
every project produces a house style nobody asked for. If the last
comparable surface used a face, choose differently unless the brand requires
it.

## Setting text well

* Balance headings so the last line is not a single orphaned word, and set
  body text to avoid single-word final lines. Use the platform properties
  for both, not manual line breaks, which break at other viewports.
* Use a hard break in a heading only when the shape survives every viewport.
* Italic descenders clip against tight line heights. Any italic at display
  size needs line height above 1 and reserved space below.
* Use real typographic quotation marks and apostrophes, real ellipses, and
  proper fractions where the face provides them.
* Numbers in tables, timers, and anything that updates use tabular figures
  so digits do not shift.
* Uppercase runs longer than a few words lose word shape and slow reading.
  Reserve uppercase for short labels.

## Delivery

* Self-host or use the framework's font pipeline. Keep third-party
  stylesheet requests off the first-paint path.
* Serve variable fonts when a range of weights is in use; one variable file
  usually costs less than three static cuts.
* Subset to the character sets needed.
* Swap to a fallback during load, and tune the fallback's metrics so the
  swap does not shift layout; an untuned fallback is a top cause of layout
  instability.
* Preload only the faces used above the fold.
