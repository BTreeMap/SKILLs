# Verb: audit

Takes a whole product, page set, or design system and returns a prioritized
remediation plan. Read-only: change nothing.

## Procedure

1. **Inventory the surface set.** Enumerate the routes, screens, or pages in
   scope and the shared component and token layer beneath them. State the
   scope and what was excluded.
2. **Extract the implicit system** from what the code uses, whatever the
   documentation claims: distinct accent colors, radius values, spacing
   values, type sizes, shadow definitions, icon families, animation
   durations. Count the distinct values per scale; nineteen spacing values
   and four accents are residue to consolidate. Audit this token layer
   first: most surface-level inconsistency is one or two bad or missing
   tokens expressed many times.
3. **Count implementations per primitive** by searching for the concept, as
   `components` directs. Several implementations of one primitive is
   normally the highest-leverage finding, since consolidating them fixes
   many inconsistency instances at once.
4. **Score each surface** on the five sweeps the spine defines. Note the
   primary goal and the friction budget per surface.
5. **Cluster findings by cause.** Twelve contrast failures from one bad
   neutral token are one finding with twelve instances. Report accessibility
   failures as their own cluster, each with the criterion it violates, since
   these carry obligations the rest do not.
6. **Rank by leverage**: instances affected multiplied by user impact,
   divided by cost to fix. Token-layer fixes almost always dominate. Cap the
   list at what can be acted on; a hundred findings is noise.
7. **Write the plan** in three horizons.

Distinguish debt from decision: keep deliberate deviations with documented
reasons out of findings, and report undocumented deviations as missing
documentation. Record a new design-system adoption under "not fixed by this
plan"; it is a refactor decision with its own verb.

## Deliverable

<template for="audit">
## Scope
{surfaces audited}; excluded: {what and why}

## System inventory
| Scale | Distinct values found | Should be | Worst offenders |
| --- | --- | --- | --- |
| Accent | {n} | 1 | {locations} |
| Radius | {n} | {n} | {locations} |
| Spacing | {n} | {n} | {locations} |
| Type size | {n} | {n} | {locations} |
| Icon family | {n} | 1 | {locations} |
| Implementations per primitive | {n} | 1 | {button, input, modal, ...} |
| Components with unclosed boolean variants | {n} | 0 | {locations} |
| Downward-import violations | {n} | 0 | {locations} |

## Ranked findings
### {n}. {cause} ({instances} instances, {severity})
Effect: {what users experience}
Locations: {where}
Fix: {the single change that resolves the cluster}
Leverage: {why this rank}

## Plan
**Now** (token layer, low risk, high spread): {items}
**Next** (component layer): {items}
**Later** (composition and flow): {items}

## Not fixed by this plan
{structural problems requiring a refactor decision}
</template>

## Completion checks

<checklist>
  <item>Scope and exclusions are stated.</item>
  <item>The implicit system was extracted from code with distinct-value counts per scale.</item>
  <item>Findings are clustered by cause, with instance counts.</item>
  <item>Ranking is by leverage and the token layer was examined first.</item>
  <item>Deliberate documented deviations were excluded from findings.</item>
  <item>The plan is split into now, next, and later, and names what it does not fix.</item>
  <item>Accessibility failures are clustered separately with the criterion each violates.</item>
</checklist>
