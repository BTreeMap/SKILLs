# Craft: component architecture

Owns component boundaries, prop APIs, duplication policy, layering, and
render cost. Compose so the second screen costs less than the first: name
each concept once, close the set of its variants, make the invalid
combination unrepresentable, and keep effects at the edges.

## Inventory before authoring

Before writing any component, search the repository for the concept by name
and by shape: the component, its variants, a hook, a utility, a token.
Duplicates are usually named differently. Find the thing that is nearly
right and extend it with a new variant. If extending would contort it, say
so and explain why a second component is the honest answer before creating
it.

A second Button, Input, Card, Modal, Select, or Table is the most damaging
habit in generated frontends: it forks behavior, fragments tokens, and
splits accessibility fixes across files. Never copy a component to make one
visual change.

## The two prices of duplication

Evaluate these two separately.

**Duplicated primitives are always a defect.** A design system claims these
things are the same thing; two Buttons falsify that claim. There is no
threshold to wait for; the second one is already wrong.

**Duplicated composition is usually fine.** Two screens arranging the same
primitives similarly are not yet an abstraction. Wait for the third
occurrence, and for the shape to stop changing, before extracting. A wrong
abstraction costs more than the duplication it replaced: every later
variation is paid as a parameter, and parameters accumulate into a god
component.

The distinguishing question: does this represent one concept the product
has, or does it merely look similar today?

## Orthogonal decomposition

**One axis of variation per component.** A component varies along one
dimension and composes for everything else. When a second independent axis
appears, compose instead of adding a prop.

**Composition over configuration.** Prefer passing content and structure to
adding a flag that switches structure internally. A component whose props
control which subtree renders is several components sharing a name.

<examples for="god-component">
  <example>
    <context>A props list grown to cover every call site: twelve booleans admit 4096 combinations, a handful are rendered, none are tested. Fix by composition, a Card that renders what it is given.</context>
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
    <context>The axes that remain as props are genuinely one axis each: a closed `variant`, a closed `size`.</context>
  </example>
</examples>

## Prop APIs that exclude the invalid

**Model variants as one closed set.** Independent flags multiply into
combinations that have no meaning, and each is a state someone will
eventually pass.

<examples for="variants">
  <example>
    <before>{ primary?: bool; secondary?: bool; danger?: bool; large?: bool; small?: bool }</before>
    <after>{ variant: 'primary' | 'secondary' | 'danger'; size: 'sm' | 'md' | 'lg' }</after>
    <context>The first admits nonsense (primary and danger simultaneously, large and small); the second is closed and total.</context>
  </example>
</examples>

**Model asynchronous collections as one closed set.** Encode the container
union `interaction` defines rather than a bag of flags such as
`{ loading: bool; error?: Error; items?: Item[] }`, which admits
contradictions and permits no exhaustiveness check. A rule about which
states must exist then becomes a build error instead of a review finding.

**Eliminate exhaustively.** Handle every case of a closed set with no
catch-all branch, so adding a variant fails the build at every site that
must change. A default branch converts a compile error into a blank region
in production.

**Require a prop only when it has no sensible default.** Make every other
prop optional with a default correct for the common case. A component
requiring six props at every call site has not chosen defaults.

**When only one call site needs a prop, compose instead of adding it.**

**Style escape hatches are for position.** A call site may pass spacing or
layout classes. Overriding color, radius, or type forks the design system at
that call site; a call site needing a different look gets a new variant
inside the component, decided once.

**Keep domain types out of primitives.** A Button that accepts a `User`
belongs at the pattern layer. Check this mechanically.

## Layer in one direction

| Layer | Contains | Knows about |
| --- | --- | --- |
| Tokens | Values only, no markup | Nothing |
| Primitives | Button, Input, Text, Stack, Icon | Tokens |
| Compounds | Field, Card, Dialog, Menu | Tokens, primitives |
| Patterns | Domain assemblies such as an entity table or a checkout form | Everything below, plus domain types |
| Routes | Data access, layout, orchestration | Everything below |

Imports point downward only; a primitive importing a pattern creates a
cycle. Keep domain knowledge at the pattern layer and above.

Effects belong at the top. Data access, mutation, storage, navigation,
randomness, and time live in routes or thin container components. Everything
below is a pure function of its inputs: testable, previewable in isolation,
and reusable in a context nobody anticipated.

## Derive, do not synchronize

Compute anything derivable from props and existing state during render. An
effect whose body copies one piece of state into another renders at least
one frame with the stale value, and desyncs the moment a path forgets to run
it.

State is the minimum that cannot be derived. Two pieces of state that must
always agree are one piece of state plus a function. Store state that
belongs in the URL in the URL.

## Cost

Treat a lookup inside a loop as a nested loop.

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
    <context>The first is quadratic in the number of rows and re-runs on every render; building the index once makes the loop linear.</context>
  </example>
</examples>

* Keys come from stable identity. An array index as a key corrupts state and
  animation as soon as the list is reordered, filtered, or prepended to.
* Memoization is keyed on value semantics. A fresh object, array, or
  function literal passed as a prop defeats it on every render, so hoist or
  memoize the value itself.
* Hoist expensive construction out of the render path: build parsers,
  formatters, collators, and regular expressions once, not per row.
* Virtualize long lists past a threshold, but preserve find-in-page and
  keyboard traversal or provide an explicit alternative.
* Measure before claiming an optimization. Memoization has its own cost;
  applied indiscriminately it is slower than the render it replaced.

## Naming

Name by concept. Appearance names go stale the first time the design
changes, and location names discourage the reuse the component exists for.

<examples for="naming">
  <example>
    <before>BlueButton, SmallCard, HomepageHero, SettingsPageTable, NewModal2</before>
    <after>Button, Card, Hero, DataTable, ConfirmDialog</after>
  </example>
</examples>

Use one concept, one name, one spelling in the code, the design files, and
the conversation. Divergent vocabulary between design and code is how two
implementations of the same thing get commissioned.
