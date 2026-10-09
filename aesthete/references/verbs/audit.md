# Verb: audit

Takes whole product, page set, or design system; returns prioritized
remediation plan. Read-only: change nothing.

## Procedure

1. **Inventory surface set.** Enumerate routes, screens, or pages in scope
   and shared component and token layer beneath them. State scope and what
   was excluded.
2. **Extract implicit system** from what code uses, whatever documentation
   claims: distinct accent colors, radius values, spacing values, type
   sizes, shadow definitions, icon families, animation durations. Count
   distinct values per scale; nineteen spacing values and four accents are
   residue to consolidate. Audit token layer first: most surface-level
   inconsistency is one or two bad or missing tokens expressed many times.
3. **Count implementations per primitive** by searching for concept, as
   `components` directs. Several implementations of one primitive: normally
   highest-leverage finding; consolidating fixes many inconsistency
   instances at once.
4. **Score each surface** on five sweeps in `signs`. Note primary goal and
   friction budget per surface.
5. **Cluster findings by cause.** Twelve contrast failures from one bad
   neutral token: one finding with twelve instances. Report accessibility
   failures as own cluster, each with criterion it violates; these carry
   obligations rest do not.
6. **Rank by leverage**: instances affected multiplied by user impact,
   divided by cost to fix. Token-layer fixes almost always dominate. Cap
   list at what can be acted on; a hundred findings is noise.
7. **Write plan** in three horizons.

Distinguish debt from decision: keep deliberate deviations with documented
reasons out of findings; report undocumented deviations as missing
documentation. New design-system adoption goes under "not fixed by this
plan": refactor decision with its own verb.

## Deliverable

```markdown
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
```

## Completion checks

- Scope and exclusions stated.
- Implicit system extracted from code with distinct-value counts per scale.
- Findings clustered by cause, with instance counts.
- Ranked by leverage; token layer examined first.
- Deliberate documented deviations excluded from findings.
- Plan split into now, next, later; names what it does not fix.
- Accessibility failures clustered separately with criterion each violates.
