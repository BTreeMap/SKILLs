# Verb: audit

Ranked sweep of a whole product, page set, or design system. Output is a
prioritized remediation plan. Change nothing.

## Procedure

1. **Inventory the surface set.** Enumerate the routes, screens, or pages in
   scope and the shared component and token layer beneath them. State the
   scope and what was excluded.
2. **Extract the implicit system.** Read what the code uses, whatever the
   documentation claims: distinct accent colors, radius values,
   spacing values, type sizes, shadow definitions, icon families, animation
   durations. Count the distinct values per scale. Nineteen spacing values
   and four accents count as residue to consolidate.
3. **Score each surface** on the five sweeps: logic, hierarchy, consistency,
   voice, structure. Note the primary goal and the friction budget per surface.
4. **Cluster findings by cause.** Twelve contrast failures from one bad
   neutral token are one finding with twelve instances.
5. **Rank by leverage**: instances affected multiplied by user impact,
   divided by cost to fix. Token-layer fixes almost always dominate.
6. **Write the plan** in three horizons.

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
{structural problems requiring a redesign decision}
</template>

## Rules

* Audit the token layer first. Most surface-level inconsistency is one or
  two bad or missing tokens expressed many times.
* Count implementations per primitive by searching for the concept;
  duplicates are usually named differently. Several implementations of one
  primitive is normally the highest-leverage finding: consolidating them
  fixes many inconsistency instances at once.
* Distinguish debt from decision. Keep deliberate deviations with documented
  reasons out of findings, and report undocumented deviations as missing
  documentation.
* Record a new design-system adoption in "not fixed by this plan". It is a
  redesign decision with its own verb.
* Cap the ranked list at what can be acted on. A hundred findings is noise.
* Report accessibility failures as their own cluster with the specific
  criterion each violates, since these carry obligations the rest do not.

## Completion checks

<checklist>
  <item>Scope and exclusions are stated explicitly.</item>
  <item>The implicit system was extracted from code with distinct-value counts per scale.</item>
  <item>Findings are clustered by cause, with instance counts.</item>
  <item>Ranking is by leverage and the token layer was examined first.</item>
  <item>Deliberate documented deviations were excluded from findings.</item>
  <item>The plan is split into now, next, and later, and names what it does not fix.</item>
  <item>Accessibility failures are clustered separately with the criterion each violates.</item>
</checklist>
