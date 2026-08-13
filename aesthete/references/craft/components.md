# Craft: component architecture

An interface is code that outlives the design that motivated it. Compose it
so the second screen costs less than the first, and the tenth costs least of
all. A codebase where every screen re-implements the same controls is not a
design system with a styling problem; it is an architecture failure that
happens to be visible.

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
the cost of every future change. It is rarely a decision; it is the result
of not looking. Look.

If the existing component is close but not sufficient, the correct move is
to extend it with a new variant, not to copy it. If extending would require
contorting it, say so explicitly and explain why a second component is the
honest answer.

## The two prices of duplication

These are different problems and the same answer to both is wrong.

**Duplicated primitives are always a defect.** A design system is precisely
the claim that these things are the same thing. Two Buttons falsify that
claim. There is no threshold to wait for, no rule of three; the second one
is already wrong.

**Duplicated composition is usually fine.** Two screens arranging the same
primitives similarly are not yet an abstraction. Wait for the third
occurrence, and for the shape to stop changing, before extracting. A wrong
abstraction is more expensive than the duplication it replaced, because
every future variation is paid as a parameter, and parameters accumulate
into the god component described below.

The distinguishing question: does this represent one concept the product
genuinely has, or does it merely look similar today?

## Orthogonal decomposition

**One axis of variation per component.** A component varies along one
dimension and composes for everything else. When a second independent axis
appears, that is a signal to compose, not to add a prop.

**Composition over configuration.** Prefer passing content and structure to
adding a flag that switches structure internally. A component whose props
control which subtree renders is several components sharing a name.

<god_component>
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
</god_component>

## Prop APIs that exclude the invalid

**Model variants as one closed set, never as independent booleans.**
Independent flags multiply into combinations that have no meaning, and each
one is a state someone will eventually pass.

<variant_modeling>
Admits nonsense (primary and danger simultaneously, large and small):
  { primary?: bool; secondary?: bool; danger?: bool; large?: bool; small?: bool }

Closed and total:
  { variant: 'primary' | 'secondary' | 'danger'; size: 'sm' | 'md' | 'lg' }
</variant_modeling>

**Model asynchronous collections as one closed set.** craft/interaction.md
defines the container states and their canonical union; encode that union
rather than a bag of flags. This is the point where type discipline and
design discipline are the same act: a design rule about which states must
exist becomes a build error when one is missing, instead of a review finding
somebody has to catch.

<flag_bag>
Admits contradictions, and no exhaustiveness check can be performed on it:
  { loading: bool; error?: Error; items?: Item[] }
</flag_bag>

**Eliminate exhaustively.** Handle every case of a closed set with no
catch-all branch, so that adding a variant fails the build at every site
that must change. A default branch converts a compile error into a blank
region in production.

**Required means no sensible default.** Everything else is optional with a
default that is correct for the common case. A component requiring six props
at every call site has not chosen defaults.

**Do not accept a prop that exists for one call site.** That is a
composition need in disguise.

**Style escape hatches are for position, not identity.** Allowing a call
site to pass spacing or layout classes is reasonable. Allowing it to
override color, radius, or type is how a design system dies one call site at
a time. If a call site needs a different look, that look is a new variant
inside the component, decided once.

**Primitives take no domain types.** A Button that accepts a `User` is not a
primitive; it is a pattern that has been filed in the wrong place. This is
mechanically checkable and worth checking.

## Layer in one direction

| Layer | Contains | Knows about |
| --- | --- | --- |
| Tokens | Values only, no markup | Nothing |
| Primitives | Button, Input, Text, Stack, Icon | Tokens |
| Compounds | Field, Card, Dialog, Menu | Tokens, primitives |
| Patterns | Domain assemblies such as an entity table or a checkout form | Everything below, plus domain types |
| Routes | Data access, layout, orchestration | Everything below |

Imports point downward only. A primitive importing a pattern is a cycle and
the beginning of an unmaintainable tree. Domain knowledge enters at the
pattern layer and never below it.

Effects belong at the top. Data access, mutation, storage, navigation,
randomness, and time live in routes or thin container components.
Everything below is a pure function of its inputs, which is what makes it
testable, previewable in isolation, and reusable in a context nobody
anticipated.

## Derive, do not synchronize

Anything computable from props and existing state is computed during render.
An effect whose body copies one piece of state into another is a bug with a
delay: it renders at least one frame with the stale value, and it desyncs
the moment a path forgets to run it.

State is the minimum that cannot be derived. Two pieces of state that must
always agree are one piece of state plus a function. State that belongs in
the URL belongs in the URL, not duplicated beside it.

## Cost

Rendering has complexity, and the same interrogation applies as anywhere
else: a lookup inside a loop is a nested loop.

<render_cost>
Quadratic in the number of rows, re-run on every render:
  rows.map(row => {
    const owner = users.find(u => u.id === row.ownerId)   // O(n) per row
    ...
  })

Build the index once, then the loop is linear:
  const byId = new Map(users.map(u => [u.id, u]))
  rows.map(row => { const owner = byId.get(row.ownerId) ... })
</render_cost>

* Keys come from stable identity. An array index as a key corrupts state and
  animation as soon as the list is reordered, filtered, or prepended to.
* Memoization is keyed on value semantics. A fresh object, array, or
  function literal passed as a prop defeats it on every render, so hoist or
  memoize the value, not just the component.
* Hoist expensive construction out of the render path: parsers, formatters,
  collators, and regular expressions are built once, not per row.
* Virtualize long lists past a threshold, but preserve find-in-page and
  keyboard traversal or provide an explicit alternative.
* Measure before claiming an optimization. Memoization has its own cost and
  applied indiscriminately it is slower than the render it replaced.

## Naming

Name by concept, never by appearance or by where it first appeared.
Appearance names go stale the first time the design changes, and location
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
