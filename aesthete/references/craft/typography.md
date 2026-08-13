# Craft: typography

Type is the interface. It carries most of the hierarchy, most of the voice,
and most of the reading effort. Get it right before touching color.

## The scale

Fix one scale and use only its steps. A ratio near 1.2 suits dense product
interfaces; near 1.333 suits marketing surfaces where display type does
expressive work. Fewer steps used consistently beats more steps used
approximately. Six to eight steps covers almost every interface.

Set the scale in a relative unit so it honors the user's browser text size.
Fixed pixel sizing for body text overrides an explicit accessibility
preference. Treat it as an accessibility defect.

## Measure and rhythm

* Body measure between roughly 45 and 75 characters. Wider loses the line
  return; narrower fragments phrases.
* Line height inverse to size: generous for body text, tightening as display
  size grows, near or slightly above 1 only at the largest display sizes.
* Line height and spacing scale should share a rhythm so text blocks align
  to the same grid as everything else.
* Paragraph spacing separates; first-line indentation is for continuous
  prose. Never use both.
* Tighten letter spacing slightly as size increases; loosen it for uppercase
  and for small text. Never letterspace lowercase body text.

## Choosing faces

Two families is the working maximum: one for text, one for display or
monospace. Three requires a reason you can state.

Choose for the job. A face for an operator console needs unambiguous digits,
distinguishable I/l/1 and O/0, and a true monospace companion for numbers
and identifiers. A face for an editorial surface needs a real italic and
sufficient weight range. Verify the family actually ships the weights and
the true italic being used before designing around them.

**Serif discipline.** Serif is not a synonym for premium, creative, or
considered, and reaching for it on that reasoning is the most common type
misjudgment in generated design. Use a serif when the surface is genuinely
editorial, literary, heritage, or when the brand specifies one, and be able
to say why that particular serif suits that particular brand. Otherwise
choose a display sans, the common default in contemporary brand work.

**Emphasis stays in the family.** Emphasize a word inside a heading with the
weight or the italic of the same family. Dropping a single word of another
family into a heading is the most visible amateur move in typography.

**Rotate.** Reusing the same two or three fashionable faces across every
project produces a house style nobody asked for. If the last comparable
surface used a face, choose differently unless the brand requires it.

## Setting text well

* Balance headings so the last line is not a single orphaned word, and set
  body text to avoid single-word final lines. The platform has properties
  for both; prefer them to manual line breaks, which break at other
  viewports.
* Never hard-break a heading to force a shape unless the shape survives
  every viewport.
* Italic descenders clip against tight line heights. Any italic at display
  size needs line height above 1 and reserved space below.
* Use real typographic quotation marks and apostrophes, real ellipses, and
  proper fractions where the face provides them.
* Numbers in tables, timers, and anything that updates use tabular figures
  so digits do not shift.
* Uppercase runs longer than a few words lose word shape and slow reading.
  Reserve uppercase for short labels.

## Delivery

* Self-host or use the framework's font pipeline. Never block first paint on
  a third-party stylesheet request.
* Serve variable fonts when a range of weights is in use; one variable file
  usually costs less than three static cuts.
* Subset to the character sets actually needed.
* Swap to a fallback rather than hiding text during load, and tune the
  fallback's metrics so the swap does not shift layout. Untuned font
  fallback is a top cause of layout instability.
* Preload only the faces used above the fold.

## Failure modes

* A scale with many near-identical steps produces hierarchy nobody can
  perceive and inconsistency everybody can.
* Display type set at a size chosen before the headline was written; the
  headline then wraps to four lines and the composition breaks.
* Grey body text chosen for elegance that fails contrast at the size it is
  set.
* Two faces that are too similar to read as a pairing and too different to
  read as one voice.
* Weight used as the only hierarchy signal in a face whose weights are close
  together.
