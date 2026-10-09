# Verb: refactor

Takes existing interface, reworks it with function preserved; returns
changes and before-and-after account per lever. Detect mode first so rework
matches problem.

## Mode detection

| Mode | Condition | Posture |
| --- | --- | --- |
| Evolve | Information architecture, content, traffic sound | Keep brand, raise craft |
| Overhaul | Visual language is problem; content and IA survive | New visuals, preserved structure and copy |
| Rebuild | Structure itself broken, or brand changing | Treat as greenfield with migration obligations |

Mode ambiguous: ask once whether existing brand is preserved or visual
language starts fresh. Otherwise infer and state mode.

## Audit before touching

Record current state before proposing anything, so working parts survive
rework.

* **Brand tokens** in use: colors, type stack, logo treatment, radii,
  spacing rhythm, motion character.
* **Information architecture**: route tree, navigation labels, conversion or
  completion paths, anchor targets.
* **Content inventory**: what exists, what carries weight, what is filler.
* **Working patterns to preserve**: recognizable hero, signature
  interaction, copy voice, hard-won accessibility fixes.
* **Patterns to retire**: broken layouts, dead ends, generated-looking
  output, performance traps.
* **Current dials**: infer VARIANCE, MOTION, DENSITY from existing interface
  as starting point.
* **Discoverability baseline**: ranking pages, titles, structured data,
  share cards. Migration damage here is highest-cost rework failure and
  least visible during work.

## Modernization levers

Apply in order; stop when brief satisfied. Earlier levers deliver more
visible improvement per unit of risk.

1. **Typography**: scale, pairing, measure, rhythm. Largest visible lift
   available, cheapest to reverse.
2. **Space and rhythm**: consistent spacing scale, section cadence, vertical
   rhythm, container widths.
3. **Color recalibration**: unify neutral family, reduce to one accent, fix
   contrast, add missing theme.
4. **State completeness**: add interaction and container states missing from
   original, per `interaction`. Usually largest usability gain in old
   interface.
5. **Motion layer**: add restrained, motivated motion to existing
   components.
6. **Composition**: restructure highest-value screens.
7. **Replacement**: rebuild block only when it cannot be salvaged.

## Never change silently

Require explicit approval; downstream systems and user habits depend on
them:

* Route structure and anchor targets.
* Primary navigation labels.
* Form field names, order, semantics (they break autofill and analytics).
* Logo and wordmark.
* Legal, consent, privacy copy.
* Any identifier instrumentation or automated tests select on.

## Rules

* Extract brand before applying any default: brand already purple stays
  purple.
* Preserve copy voice and content unless rewrite was requested.
* Never regress accessibility win: existing focus states, alt text, keyboard
  paths, contrast are a floor.
* Audit shows interface sound and request is aesthetic restlessness: say so,
  propose smallest lever that satisfies it.

## Completion checks

<checklist>
  <item>Mode detected and stated before any change.</item>
  <item>Audit completed and recorded, including current dials and discoverability baseline.</item>
  <item>Brand tokens extracted and honored ahead of any default.</item>
  <item>Levers applied in order, stopped at brief.</item>
  <item>Missing interaction states added.</item>
  <item>Nothing on never-change-silently list modified without approval.</item>
  <item>No accessibility behavior regressed.</item>
  <item>Changes reported per lever with before and after.</item>
</checklist>
