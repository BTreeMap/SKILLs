# Craft: typography

Get type right before touching color.

## The scale

Fix one scale, use only its steps; six to eight steps covers almost every
interface. Adjacent steps perceptibly distinct: many near-identical steps
produce hierarchy nobody can perceive and inconsistency everybody can. Ratio
near 1.2 suits dense product interfaces; near 1.333 suits marketing surfaces
where display type does expressive work.

Set scale in relative unit so it honors user's browser text size; fixed
pixel sizing for body text overrides explicit accessibility preference.

Size display type against headline actually written, not one imagined: size
chosen first wraps real headline to four lines, breaks composition.

## Measure and rhythm

* Body measure roughly 45 to 75 characters. Wider loses line return;
  narrower fragments phrases.
* Line height inverse to size: generous for body, tightening as display size
  grows, near or slightly above 1 only at largest display sizes.
* Line height and spacing scale share rhythm so text blocks align to same
  grid as everything else.
* Paragraph spacing separates; first-line indentation is for continuous
  prose. Use exactly one of the two.
* Tighten letter spacing slightly as size increases; loosen only for
  uppercase and small text.

## Choosing faces

Two families is working maximum: one for text, one for display or monospace.
Three requires reason you can state. Pair must be distinct enough to read as
pairing or close enough to read as one voice, never in between.

Choose for job. Operator console face needs unambiguous digits,
distinguishable I/l/1 and O/0, true monospace companion for numbers and
identifiers. Editorial face needs real italic and sufficient weight range.
Verify family ships weights and true italic used before designing around
them. Weights close together: weight not the only hierarchy signal.

**Serif discipline.** Reaching for serif because it feels premium, creative,
or considered is most common type misjudgment in generated design. Use serif
when surface is editorial, literary, or heritage, or brand specifies one;
state why that serif suits that brand. Otherwise display sans, common
default in contemporary brand work.

**Emphasis stays in family.** Emphasize word inside heading with weight or
italic of same family.

**Rotate faces.** Same two or three fashionable faces across every project
produce house style nobody asked for. Last comparable surface used a face:
choose differently unless brand requires it.

## Setting text well

* Balance headings so last line is not single orphaned word; set body text
  to avoid single-word final lines. Use platform properties for both, not
  manual line breaks, which break at other viewports.
* Hard break in heading only when shape survives every viewport.
* Italic descenders clip against tight line heights. Any italic at display
  size needs line height above 1 and reserved space below.
* Real typographic quotation marks and apostrophes, real ellipses, proper
  fractions where face provides them.
* Numbers in tables, timers, anything updating: tabular figures so digits do
  not shift.
* Uppercase runs longer than few words lose word shape, slow reading.
  Uppercase only for short labels.

## Delivery

* Self-host or use framework's font pipeline. Keep third-party stylesheet
  requests off first-paint path.
* Variable fonts when range of weights in use; one variable file usually
  costs less than three static cuts.
* Subset to needed character sets.
* Swap to fallback during load; tune fallback's metrics so swap does not
  shift layout. Untuned fallback is top cause of layout instability.
* Preload only faces used above fold.
