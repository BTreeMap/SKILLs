# Craft: component architecture

Compose so second screen costs less than first: name each concept once,
close set of its variants, make invalid combination unrepresentable, keep
effects at edges.

## Inventory before authoring

Before writing any component, search repository for concept by name and by
shape: component, its variants, hook, utility, token. Duplicates usually
named differently. Find thing nearly right; extend it with new variant.
Extending would contort it: say so, explain why second component is honest
answer, before creating it.

Second Button, Input, Card, Modal, Select, or Table is most damaging habit
in generated frontends: forks behavior, fragments tokens, splits
accessibility fixes across files. Never copy component to make one visual
change.

## The two prices of duplication

Evaluate these two separately.

**Duplicated primitives always defect.** Design system claims these are same
thing; two Buttons falsify that claim. No threshold to wait for; second one
already wrong.

**Duplicated composition usually fine.** Two screens arranging same
primitives similarly are not yet abstraction. Wait for third occurrence, and
for shape to stop changing, before extracting. Wrong abstraction costs more
than duplication it replaced: every later variation paid as parameter;
parameters accumulate into god component.

Distinguishing question: does this represent one concept product has, or
merely look similar today?

## Orthogonal decomposition

**One axis of variation per component.** Component varies along one
dimension, composes for everything else. Second independent axis appears:
compose instead of adding prop.

**Composition over configuration.** Prefer passing content and structure to
adding flag that switches structure internally. Component whose props
control which subtree renders is several components sharing a name.

<examples for="god-component">
  <example>
    <context>Props list grown to cover every call site: twelve booleans admit 4096 combinations, handful rendered, none tested. Fix by composition: Card renders what it is given.</context>
    <before>
      <Card
        showHeader showFooter showAvatar showBadge compact bordered
        elevated clickable headerAlign footerVariant ... />
    </before>
    <after>
      <Card>
        <Card.Header>...</Card.Header>
        <Card.Body>...</Card.Body>
      </Card>
    </after>
    <context>Axes remaining as props are genuinely one axis each: closed `variant`, closed `size`.</context>
  </example>
</examples>

## Prop APIs that exclude the invalid

**Model variants as one closed set.** Independent flags multiply into
meaningless combinations; each is a state someone will eventually pass.

<examples for="variants">
  <example>
    <before>{ primary?: bool; secondary?: bool; danger?: bool; large?: bool; small?: bool }</before>
    <after>{ variant: 'primary' | 'secondary' | 'danger'; size: 'sm' | 'md' | 'lg' }</after>
    <context>First admits nonsense (primary and danger simultaneously, large and small); second is closed and total.</context>
  </example>
</examples>

**Model asynchronous collections as one closed set.** Encode container union
`interaction` defines, not bag of flags such as
`{ loading: bool; error?: Error; items?: Item[] }`, which admits
contradictions and permits no exhaustiveness check. Rule about which states
must exist then becomes build error instead of review finding.

**Eliminate exhaustively.** Handle every case of closed set with no
catch-all branch, so adding variant fails build at every site that must
change. Default branch converts compile error into blank region in
production.

**Require prop only when it has no sensible default.** Every other prop
optional with default correct for common case. Component requiring six props
at every call site has not chosen defaults.

**Only one call site needs prop: compose instead of adding it.**

**Style escape hatches are for position.** Call site may pass spacing or
layout classes. Overriding color, radius, or type forks design system at
that call site; call site needing different look gets new variant inside
component, decided once.

**Keep domain types out of primitives.** Button accepting `User` belongs at
pattern layer. Check mechanically.

## Layer in one direction

| Layer | Contains | Knows about |
| --- | --- | --- |
| Tokens | Values only, no markup | Nothing |
| Primitives | Button, Input, Text, Stack, Icon | Tokens |
| Compounds | Field, Card, Dialog, Menu | Tokens, primitives |
| Patterns | Domain assemblies such as entity table or checkout form | Everything below, plus domain types |
| Routes | Data access, layout, orchestration | Everything below |

Imports point downward only; primitive importing pattern creates cycle.
Domain knowledge at pattern layer and above.

Effects belong at top. Data access, mutation, storage, navigation,
randomness, time live in routes or thin container components. Everything
below is pure function of its inputs: testable, previewable in isolation,
reusable in context nobody anticipated.

## Derive, do not synchronize

Compute anything derivable from props and existing state during render.
Effect whose body copies one piece of state into another renders at least
one frame with stale value, desyncs the moment a path forgets to run it.

State is minimum that cannot be derived. Two pieces of state that must
always agree: one piece of state plus function. State belonging in URL goes
in URL.

## Cost

Treat lookup inside loop as nested loop.

<examples for="render-cost">
  <example>
    <before>
      rows.map(row => {
        const owner = users.find(u => u.id === row.ownerId)   // O(n) per row
        ...
      })
    </before>
    <after>
      const byId = new Map(users.map(u => [u.id, u]))
      rows.map(row => { const owner = byId.get(row.ownerId) ... })
    </after>
    <context>First is quadratic in number of rows, re-runs every render; building index once makes loop linear.</context>
  </example>
</examples>

* Keys come from stable identity. Array index as key corrupts state and
  animation once list is reordered, filtered, or prepended to.
* Memoization keyed on value semantics. Fresh object, array, or function
  literal passed as prop defeats it every render: hoist or memoize value
  itself.
* Hoist expensive construction out of render path: build parsers,
  formatters, collators, regular expressions once, not per row.
* Virtualize long lists past threshold, but preserve find-in-page and
  keyboard traversal or provide explicit alternative.
* Measure before claiming optimization. Memoization has own cost; applied
  indiscriminately it is slower than render it replaced.

## Naming

Name by concept. Appearance names go stale first time design changes;
location names discourage reuse component exists for.

<examples for="naming">
  <example>
    <before>BlueButton, SmallCard, HomepageHero, SettingsPageTable, NewModal2</before>
    <after>Button, Card, Hero, DataTable, ConfirmDialog</after>
  </example>
</examples>

One concept, one name, one spelling in code, design files, conversation.
Divergent vocabulary between design and code is how two implementations of
same thing get commissioned.
