# Supplied material

Design documents routinely carry contrast failures, stale accessibility
claims, missing states, rules written for different scope. Adopt what holds,
verify rest, report every divergence.

## Procedure

1. **Inventory.** List what was supplied: tokens, component specifications,
   composition rules, prohibitions, stated gaps. Note what is absent;
   absences drive step 5.
2. **Apply precedence.** Supplied palette overrides document's colors and
   nothing else. Document keeps its type, spacing, radius, component,
   composition decisions.
3. **Map palette to roles** (below).
4. **Verify against floor** (below).
5. **Fill gaps by deriving values from supplied system**, following its own
   logic so each value looks native; report every value derived. Missing
   dark theme, states, responsive rules, semantic colors all common.
6. **Report** (below), naming every failing token adopted and why.

## Mapping a palette to roles

Make mapping once; write it down. Identify, in this order:

1. **Accent**: most saturated color, or one source names as primary. Exactly
   one, however many palette offers.
2. **Ink and canvas**: darkest and lightest members. Neither pure black nor
   pure white unless palette insists.
3. **Neutral family**: desaturated members; must read as one temperature.
   Palette mixes warm and cool neutrals: pick one, derive rest.
4. **Remaining members**: assign to secondary surfaces, or hold in reserve.
   Use only colors with assigned roles; five supplied colors do not obligate
   five roles.

Palette arrives as stepped scales: ramp is role source. Light step for
canvas, mid step for borders and secondary text, dark step for ink, accent's
own mid and dark steps for rest and active states. Every value interface
needs should already exist in ramp.

Derive what is missing from palette's own geometry: hover and active states
are lightness steps on accent; surface elevation steps are lightness steps
on canvas. Fill role with existing hue.

Prefer palette's own members where one reads correctly for meaning. None
does: import minimum, keep them distinguishable from accent, declare them as
additions in report. Danger must never be accent, or destructive actions
stop reading as destructive.

## Verifying against the floor

Compute each contrast ratio from two composited values; document's claim is
unverified. `a11y` owns thresholds and exemptions; apply them to every
supplied pairing before adopting any of it.

Check at minimum: every text role against every surface it sits on; accent
against its on-color at sizes used; secondary and muted text against both
canvas and any tinted card; borders identifying control; both themes if two
exist.

Verify every accessibility claim against current specification. Documents
commonly cite superseded thresholds or wrong conformance level; claim of
non-compliance can be as wrong as claim of compliance.

## Resolving a conflict with the floor

Satisfy floor, preserve brand intent. Resolve by derivation, in this order;
report which step used:

1. **Restrict by size.** Brand color failing normal-text threshold often
   passes large-text threshold. Keep it for display type and large fills;
   compliant variant for small text. Usually preserves brand where most
   visible.
2. **Use darker or lighter ramp step.** Most systems already ship active or
   pressed variant that passes. Promote it to text-bearing use; keep
   original for fills.
3. **Change on-color.** Mid-tone accent frequently fails against white and
   passes against system's own ink.
4. **Adjust lightness within hue**, as little as threshold requires,
   preserving hue and saturation so brand still reads.
5. **Report as unresolvable** only if all four fail; name what document must
   change.

Never resolve by silently shipping failure, abandoning brand color entirely,
or claiming floor does not apply.

## Rules that survive supplied material

Supplied documents govern appearance; function still applies.

* **Interaction states are function.** Unspecified hover, focus, loading, or
  error states are gaps: fill them in system's own language, report them.
  Document can legitimately forbid particular hover *treatment*; it cannot
  forbid focus visibility or error state.
* **Document's prohibitions bind its own scope.** Rule about what to
  document is not rule about what to implement; rule about marketing surface
  does not govern application surface.

## Report

Emit before building.

```markdown
## Adopted
{tokens and rules taken as given}

## Overridden by palette
{document color} -> {palette color and its role}

## Floor conflicts
{token}: {measured ratio} against {surface}, needs {threshold}
Resolution: {which derivation, and the resulting value}

## Corrected claims
{claim in the document}: {what the specification actually says}

## Derived to fill gaps
{role or state}: {derived value and the logic used}

## Unresolved
{what the document must decide}
```

## Completion checks

Run with `preflight` before declaring done.

- Precedence applied in order: palette overrode document's colors, document
  overrode this skill's defaults, accessibility floor overrode everything.
- Every supplied token pairing used measured for contrast, including
  secondary text on tinted surfaces.
- Every floor conflict resolved by derivation and reported, brand preserved
  wherever threshold allowed.
- Document's accessibility claims verified against specification.
- Gaps document left derived from its own logic and reported.
