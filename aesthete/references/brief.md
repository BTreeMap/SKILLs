# Supplied material

Owns ingestion of a supplied design document and color palette: precedence,
palette-to-role mapping, verification, conflict resolution, gap filling,
reporting, and the supplied-material checks of the ship gate.

Design documents routinely carry contrast failures, stale accessibility
claims, missing states, and rules written for a different scope. Adopt what
holds, verify the rest, and report every divergence.

## Procedure

1. **Inventory.** List what was supplied: tokens, component specifications,
   composition rules, prohibitions, and stated gaps. Note what is absent;
   absences drive step 5.
2. **Apply precedence.** A supplied palette overrides the document's colors
   and nothing else. The document keeps its type, spacing, radius,
   component, and composition decisions.
3. **Map the palette to roles** (below).
4. **Verify against the floor** (below).
5. **Fill gaps by deriving values from the supplied system**, following its
   own logic so each value looks native, and report every value derived.
   Missing dark theme, states, responsive rules, and semantic colors are all
   common.
6. **Report** (below), naming every failing token you adopted and why.

## Mapping a palette to roles

A palette is colors; a system needs roles. Make the mapping once and write
it down. Identify, in this order:

1. **Accent**: the most saturated color, or the one the source names as
   primary. Exactly one, however many the palette offers.
2. **Ink and canvas**: the darkest and lightest members. Neither should be
   pure black or pure white unless the palette insists.
3. **Neutral family**: the desaturated members, which must read as one
   temperature. If the palette mixes warm and cool neutrals, pick one and
   derive the rest.
4. **Remaining members**: assign to secondary surfaces, or hold them in
   reserve. Use only colors with assigned roles; five supplied colors do not
   obligate five roles.

When the palette arrives as stepped scales, the ramp is the role source:
select a light step for canvas, a mid step for borders and secondary text, a
dark step for ink, and the accent's own mid and dark steps for rest and
active states. Every value the interface needs should already exist in the
ramp.

Derive what is missing from the palette's own geometry: hover and active
states are lightness steps on the accent, and surface elevation steps are
lightness steps on the canvas. Fill a role with an existing hue.

Prefer the palette's own members where one reads correctly for the meaning.
Where none does, import the minimum, keep them distinguishable from the
accent, and declare them as additions in the report. Danger must never be
the accent, or destructive actions stop reading as destructive.

## Verifying against the floor

Compute each contrast ratio from the two composited values; the document's
claim is unverified. `a11y` owns the thresholds and exemptions; apply them
to every supplied pairing before adopting any of it.

Check at minimum: every text role against every surface it sits on, the
accent against its on-color at the sizes used, secondary and muted text
against both the canvas and any tinted card, borders that identify a
control, and both themes if two exist.

Verify every accessibility claim against the current specification.
Documents commonly cite superseded thresholds or the wrong conformance
level, and a claim of non-compliance can be as wrong as a claim of
compliance.

## Resolving a conflict with the floor

Satisfy the floor and preserve brand intent. Resolve by derivation, in this
order, and report which step was used:

1. **Restrict by size.** A brand color failing the normal-text threshold
   often passes the large-text threshold. Keep it for display type and large
   fills; use a compliant variant for small text. This usually preserves the
   brand where it is most visible.
2. **Use the darker or lighter ramp step.** Most systems already ship an
   active or pressed variant that passes. Promote it to the text-bearing use
   and keep the original for fills.
3. **Change the on-color.** A mid-tone accent frequently fails against white
   and passes against the system's own ink.
4. **Adjust lightness within the hue**, as little as the threshold requires,
   preserving hue and saturation so the brand still reads.
5. **Report as unresolvable** only if all four fail, and name what the
   document must change.

Never resolve by silently shipping the failure, by abandoning the brand
color entirely, or by claiming the floor does not apply.

## Rules that survive supplied material

Supplied documents govern appearance; function still applies.

* **Interaction states are function.** Treat unspecified hover, focus,
  loading, or error states as gaps: fill them in the system's own language
  and report them. A document can legitimately forbid a particular hover
  *treatment*; it cannot forbid focus visibility or an error state.
* **A document's prohibitions bind its own scope.** A rule about what to
  document is not a rule about what to implement, and a rule about a
  marketing surface does not govern an application surface.

## Report

Emit before building.

<template for="supplied-material">
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
</template>

## Completion checks

Run these with `preflight` before declaring done.

<checklist>
  <item>Precedence applied in order: the palette overrode the document's colors, the document overrode this skill's defaults, and the accessibility floor overrode everything.</item>
  <item>Every supplied token pairing used was measured for contrast, including secondary text on tinted surfaces.</item>
  <item>Every floor conflict was resolved by derivation and reported, with the brand preserved wherever the threshold allowed.</item>
  <item>Accessibility claims made by the document were verified against the specification.</item>
  <item>Gaps the document left were derived from its own logic and reported.</item>
</checklist>
