# Supplied material

Owns ingestion of a supplied design document and color palette: precedence,
palette-to-role mapping, verification, conflict resolution, gap filling, and
reporting.

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
4. **Verify against the accessibility floor** (below). This is the step that
   makes adoption safe, and the step most often skipped.
5. **Fill gaps by deriving values from the supplied system.** A missing value
   follows the system's own logic so it looks native.
6. **Report** (below). Name every failing token you adopted and why.

## Mapping a palette to roles

A palette is colors; a system needs roles. The mapping is a decision, made
once and written down. Identify, in this order:

1. **Accent**: the most saturated color, or the one the source names as
   primary. Exactly one, regardless of how many the palette offers.
2. **Ink and canvas**: the darkest and lightest members. Neither should be
   pure black or pure white unless the palette insists.
3. **Neutral family**: the desaturated members, which must read as one
   temperature. A palette mixing warm and cool neutrals forces a choice;
   pick one and derive the rest.
4. **Remaining members**: assign to secondary surfaces, or hold them in
   reserve. Use only colors with assigned roles; five supplied colors do not
   obligate five roles.

**A ramp is the role source.** When the palette arrives as stepped scales,
select steps: a light step for canvas, a mid step for borders and
secondary text, a dark step for ink, and the accent's own mid and dark steps
for rest and active states. Every value the interface
needs should already exist in the ramp.

**Derive what is missing from the palette's own geometry.** Hover and active
states are lightness steps on the accent. Surface elevation steps are
lightness steps on the canvas. Use an existing hue to fill a role.

Prefer the palette's own members where one reads correctly for the meaning.
Where none does, import the minimum, keep them distinguishable from the
accent, and declare them as additions in the report. Danger must never be
the accent, or destructive actions stop reading as destructive.

## Verifying against the floor

Compute the contrast ratio from the two composited values; the document's
claim is unverified. Thresholds and their exemptions are owned by `a11y`;
apply them to every supplied pairing before adopting any of it.

Check at minimum: every text role against every surface it sits on, the
accent against its on-color at the sizes actually used, secondary and muted
text against both the canvas and any tinted card, borders that identify a
control, and both themes if two exist.

Verify every accessibility claim against the current specification.
Documents commonly cite superseded thresholds or the wrong conformance
level, and a claim of non-compliance can be as wrong as a claim of
compliance.

## Resolving a conflict with the floor

Satisfy the floor and preserve brand intent. Resolve conflicts by
derivation, in this order, and report which was used:

1. **Restrict by size.** A brand color failing the normal-text threshold
   often passes the large-text threshold. Keep it for display type and
   large fills; use a compliant variant for small text. This usually
   preserves the brand exactly where it is most visible.
2. **Use the darker or lighter ramp step.** Most systems already ship an
   active or pressed variant that passes. Promote it to the text-bearing
   use and keep the original for fills.
3. **Change the on-color.** A mid-tone accent frequently fails against white
   and passes against the system's own ink.
4. **Adjust lightness within the hue**, as little as the threshold requires,
   preserving hue and saturation so the brand still reads.
5. **Report as unresolvable** only if all four fail, and name what the
   document must change.

Never resolve by silently shipping the failure, by abandoning the brand
color entirely, or by claiming the floor does not apply.

## Rules that survive supplied material

Supplied documents govern appearance. Function still applies.

* **Interaction states are function.** Treat unspecified hover,
  focus, loading, or error states as gaps. Fill them in the system's own
  language and report them. A document can legitimately forbid a particular
  hover *treatment*; it cannot forbid focus visibility or an error state.
* **Report every gap you fill.** Missing dark theme, missing states, missing
  responsive rules, and missing semantic colors are all common. Derive each
  value, then say what you derived.
* **A document's prohibitions bind its own scope.** A rule about what to
  document is not a rule about what to implement, and a rule about a
  marketing surface does not govern an application surface.

## Report

Emit before building.

<supplied_material_report>
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
</supplied_material_report>
