# Verb: redesign

Rework an existing interface. Misclassifying the mode is the largest source
of bad redesign output, so mode detection is the first action.

## Mode detection

| Mode | Condition | Posture |
| --- | --- | --- |
| Evolve | Information architecture, content, and traffic are sound | Keep the brand, raise the craft |
| Overhaul | Visual language is the problem; content and IA survive | New visuals, preserved structure and copy |
| Rebuild | Structure itself is broken, or the brand is genuinely changing | Treat as greenfield with migration obligations |

If genuinely ambiguous, ask once: whether the existing brand is preserved or
the visual language starts fresh. Otherwise infer and state the mode.

## Audit before touching

Document the current state before proposing anything. Skipping this step is
how redesigns delete the things that were working.

* **Brand tokens** in actual use: colors, type stack, logo treatment, radii,
  spacing rhythm, motion character.
* **Information architecture**: route tree, navigation labels, conversion or
  completion paths, anchor targets.
* **Content inventory**: what exists, what carries weight, what is filler.
* **Working patterns to preserve**: the recognizable hero, the signature
  interaction, the copy voice, hard-won accessibility fixes.
* **Patterns to retire**: broken layouts, dead ends, generated-looking
  output, performance traps.
* **Current dials**: infer VARIANCE, MOTION, and DENSITY from the existing
  interface. That reading, not the baseline, is the starting point.
* **Discoverability baseline**: ranking pages, titles, structured data, and
  share cards. Migration damage here is the highest-cost redesign failure
  and the least visible during the work.

## Modernization levers

Apply in order and stop when the brief is satisfied. Earlier levers deliver
more visible improvement per unit of risk.

1. **Typography**: scale, pairing, measure, and rhythm. The largest visible
   lift available, and the cheapest to reverse.
2. **Space and rhythm**: consistent spacing scale, section cadence,
   vertical rhythm, container widths.
3. **Color recalibration**: unify the neutral family, reduce to one accent,
   fix contrast, add the missing theme.
4. **State completeness**: add the interaction and container states the
   original never shipped, per `interaction`. Usually the single
   largest usability gain in an old interface.
5. **Motion layer**: add restrained, motivated motion to existing
   components.
6. **Composition**: restructure the highest-value screens.
7. **Replacement**: rebuild a block only when it cannot be salvaged.

## Never change silently

Requires explicit approval, because downstream systems and user habits
depend on them:

* Route structure and anchor targets.
* Primary navigation labels.
* Form field names, order, and semantics, which break autofill and analytics.
* Logo and wordmark.
* Legal, consent, and privacy copy.
* Any identifier that instrumentation or automated tests select on.

## Rules

* Extract the brand before applying any default. A brand that is already
  purple stays purple; the anti-default rules govern unbriefed choices, not
  existing identity.
* Preserve the copy voice unless a rewrite was requested. Visual
  modernization is not a content rewrite.
* Never regress an accessibility win: existing focus states, alt text,
  keyboard paths, and contrast are a floor.
* Deliver a before-and-after account per lever applied, so the change is
  reviewable rather than a wholesale replacement.
* If the audit shows the interface is sound and the request is aesthetic
  restlessness, say so and propose the smallest lever that satisfies it.

## Completion checks

<validation_checklist>
  <item>Mode was detected and stated before any change.</item>
  <item>The audit was completed and recorded, including current dials and discoverability baseline.</item>
  <item>Brand tokens were extracted and honored ahead of any default.</item>
  <item>Levers were applied in order and stopped at the brief.</item>
  <item>Missing interaction states were added, not just visuals refreshed.</item>
  <item>Nothing on the never-change-silently list was modified without approval.</item>
  <item>No accessibility behavior regressed.</item>
  <item>Changes are reported per lever with before and after.</item>
</validation_checklist>
