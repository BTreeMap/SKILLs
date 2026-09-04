# Craft: component architecture

An interface is code that outlives the design that motivated it. Compose it
so the second screen costs less than the first, and the tenth costs least of
all. When every screen re-implements the same controls, the problem is the
architecture.

Owns component boundaries, prop APIs, duplication policy, layering, and
render cost. Apply the discipline a type theorist applies to a domain model:
name the concept once, close the set of its variants, make the invalid
combination unrepresentable, and keep effects at the edges.

## Inventory before authoring

Mandatory before writing any component. Search the repository for the
concept by name and by shape: the component, its variants, a hook, a
utility, a token. Look for the thing that is nearly right and extend it.

Authoring a second Button, Input, Card, Modal, Select, or Table is the most
damaging habit in generated frontends. Each duplicate forks behavior,
fragments tokens, splits accessibility fixes across files, and multiplies
the cost of every future change.

When the existing component is close but not sufficient, extend it with a
new variant. If extending would require contorting it, say so explicitly
and explain why a second component is the honest answer.

## The two prices of duplication

**Duplicated primitives are always a defect.** A design system is the claim
that these things are the same thing. Two Buttons falsify that claim. There
is no threshold to wait for; the second one is already wrong.

**Duplicated composition is usually fine.** Two screens arranging the same
primitives similarly are not yet an abstraction. Wait for the third
occurrence, and for the shape to stop changing, before extracting. A wrong
abstraction costs more than the duplication it replaced: every future
variation is paid as a parameter, and parameters accumulate into the god
component below.

The distinguishing question: does this represent one concept the product
genuinely has, or does it merely look similar today?

## Orthogonal decomposition

**One axis of variation per component.** A component varies along one
dimension and composes for everything else. When a second independent axis
appears, compose instead of adding a prop.

**Composition over configuration.** Prefer passing content and structure to
adding a flag that switches structure internally. A component whose props
control which subtree renders is several components sharing a name.

<god-component>
Symptom: a props list that has grown to cover every call site.

  <Card
    showHeader showFooter showAvatar showBadge compact bordered
    elevated clickable headerAlign footerVariant ... />

Twelve booleans admit 4096 combinations. A handful are rendered, none are
tested, and the component's body is a thicket of conditionals nobody can
change safely.

Fix by composition: a Card that renders what it is given.

  <Card>
    <Card.Header>...</Card.Header>
    <Card.Body>...</Card.Body>
  </Card>

The axes that remain as props are the ones that are genuinely one axis:
a closed `variant`, a closed `size`.
</god-component>

## Prop APIs that exclude the invalid

**Model variants as one closed set.**
Independent flags multiply into combinations that have no meaning, and each
one is a state someone will eventually pass.

<variant-modeling>
Admits nonsense (primary and danger simultaneously, large and small):
  { primary?: bool; secondary?: bool; danger?: bool; large?: bool; small?: bool }

Closed and total:
  { variant: 'primary' | 'secondary' | 'danger'; size: 'sm' | 'md' | 'lg' }
</variant-modeling>

**Model asynchronous collections as one closed set.** `interaction`
defines the container states and their canonical union; encode that union
rather than a bag of flags. A design rule about which states must exist then
becomes a build error when one is missing, instead of a review finding
somebody has to catch.

<flag-bag>
Admits contradictions, and no exhaustiveness check can be performed on it:
  { loading: bool; error?: Error; items?: Item[] }
</flag-bag>

**Eliminate exhaustively.** Handle every case of a closed set with no
catch-all branch, so that adding a variant fails the build at every site
that must change. A default branch converts a compile error into a blank
region in production.

**Require a prop only when it has no sensible default.** Make every other
prop optional with a default that is correct for the common case. A component
requiring six props at every call site has not chosen defaults.

**When only one call site needs a prop, compose instead of adding it.**

**Style escape hatches are for position.** Allowing a call
site to pass spacing or layout classes is reasonable. Allowing it to
override color, radius, or type forks the design system at that call site.
If a call site needs a different look, that look is a new variant inside the
component, decided once.

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

Imports point downward only. A primitive importing a pattern creates a
cycle. Keep domain knowledge at the pattern layer and above it.

Effects belong at the top. Data access, mutation, storage, navigation,
randomness, and time live in routes or thin container components.
Everything below is a pure function of its inputs, which makes it testable,
previewable in isolation, and reusable in a context nobody anticipated.

## Derive, do not synchronize

Anything computable from props and existing state is computed during render.
An effect whose body copies one piece of state into another renders at least
one frame with the stale value, and desyncs the moment a path forgets to run
it.

State is the minimum that cannot be derived. Two pieces of state that must
always agree are one piece of state plus a function. Store state that belongs
in the URL in the URL.

## Cost

Treat a lookup inside a loop as a nested loop.

<render-cost>
Quadratic in the number of rows, re-run on every render:
  rows.map(row => {
    const owner = users.find(u => u.id === row.ownerId)   // O(n) per row
    ...
  })

Build the index once, then the loop is linear:
  const byId = new Map(users.map(u => [u.id, u]))
  rows.map(row => { const owner = byId.get(row.ownerId) ... })
</render-cost>

* Keys come from stable identity. An array index as a key corrupts state and
  animation as soon as the list is reordered, filtered, or prepended to.
* Memoization is keyed on value semantics. A fresh object, array, or
  function literal passed as a prop defeats it on every render, so hoist or
  memoize the value itself.
* Hoist expensive construction out of the render path: parsers, formatters,
  collators, and regular expressions are built once, not per row.
* Virtualize long lists past a threshold, but preserve find-in-page and
  keyboard traversal or provide an explicit alternative.
* Measure before claiming an optimization. Memoization has its own cost and
  applied indiscriminately it is slower than the render it replaced.

## Naming

Name by concept. Appearance names go stale the first time the design changes, and location
names discourage the reuse the component exists for.

<naming>
Stale on redesign, or discourages reuse:
  BlueButton, SmallCard, HomepageHero, SettingsPageTable, NewModal2

Names the concept:
  Button, Card, Hero, DataTable, ConfirmDialog
</naming>

One concept, one name, one spelling, used in the code, the design files, and
the conversation. Divergent vocabulary between design and code is how two
implementations of the same thing get commissioned.

## Failure modes

* Writing a component without searching for the one that exists, producing
  the third Button in the tree.
* Extracting an abstraction from two examples, then paying for the wrong
  guess with a parameter for every subsequent difference.
* A boolean prop added per call site until the combinations exceed anything
  anyone has rendered.
* A catch-all branch that silently renders nothing when a new variant
  arrives.
* Domain types reaching down into primitives, so the button cannot be used
  anywhere else.
* An effect synchronizing derived state, shipping a stale frame and an
  eventual desync.
* A lookup inside a row loop, quadratic and re-run on every keystroke.
* Copying a component to make one visual change, permanently forking its
  accessibility behavior.
