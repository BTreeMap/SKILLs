# Design systems

Do not hand-author what an official system already provides, and do not
claim a system's name for a hand-rolled approximation of it.

## Selection order

1. **What the repository already uses.** Overwhelmingly the right answer.
   Consistency with the existing tree beats any system's individual merit.
2. **The system the domain expects or requires.** Some platforms and sectors
   effectively mandate one; using anything else creates a product that feels
   foreign or fails a compliance expectation.
3. **A foundation you extend**, when the brand expression is a differentiator
   but the component behavior is not.
4. **Hand-composed**, only when the visual identity is itself the product.
   This is the most expensive option and is chosen far more often than it is
   justified.

## Matching a brief to a foundation

| The brief reads as | Reach for |
| --- | --- |
| Microsoft-adjacent or enterprise productivity | Fluent |
| Android-adjacent or Material-flavored product | Material |
| Enterprise analytics with dense data | Carbon |
| An app surface inside a commerce platform's admin | That platform's own system, which is usually required |
| Atlassian-adjacent product surface | Atlassian's system |
| Developer tooling or a code-hosting community surface | Primer, with its brand variant for marketing |
| A UK public-sector service | GOV.UK Frontend, which is effectively expected |
| A US federal or civic service | The US Web Design System |
| Accessible unstyled foundation, own the visual layer | A headless primitive library plus your own tokens |
| Modern product where you want to own the component source | A copy-in component collection, always customized |
| Fast conventional build with no brand ambition | An established general-purpose framework |

Verify the current package name, version, and installation procedure from
the system's own documentation at the time of use. Do not install from
memory: package names, entry points, and framework support change.

## Rules

* **One system per tree.** Never mix two component systems. The result
  inherits the constraints of both and the coherence of neither.
* **Use it or replace it.** Overriding a large share of a system's tokens
  means the wrong system was chosen. Say so and change the decision rather
  than fighting it component by component.
* **Theme through the intended mechanism.** Every mature system has a
  theming layer. Reaching around it with overrides breaks on upgrade.
* **Set the theme once** at the application root, never per section.
* **Copy-in components are a starting point, not a deliverable.** Shipping
  them at default values produces the recognizable unmodified look. Adapt
  radii, spacing, type, and color to the project's tokens.
* **Read the system's own guidance** before composing with it. Most encode
  decisions about density, elevation, and motion that a hand-composed layout
  will contradict.

## Aesthetics are not systems

These are visual directions with no official package. Implement them
honestly with platform primitives, and describe them accurately.

| Direction | Honest implementation |
| --- | --- |
| Frosted or translucent material | Backdrop filtering, layered borders, and highlight overlays, with a solid high-contrast fallback for reduced-transparency and unsupported cases |
| Tile grids of mixed sizes | A grid with varied cell spans; no library owns this |
| Brutalist | Native elements, monospace, unornamented borders |
| Editorial | Type, asymmetric grid, and space; no library |
| Terminal or hacker | Monospace with a restrained accent |
| Mesh or aurora backgrounds | Layered gradients or vector art, on a non-interactive layer |
| Kinetic type | CSS animation and scroll-linked timelines |

A proprietary platform's named material is documented by its vendor for that
vendor's platforms. A web build of it is an approximation, must be labeled as
one in code comments, and must not be presented to the user as the real
system. Any translucent material needs a solid fallback that preserves
contrast when transparency is reduced or unsupported.
