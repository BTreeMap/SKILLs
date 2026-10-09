# Design systems

Use what official system already provides; name hand-rolled approximations
honestly.

## Selection order

1. **What repository already uses.** Consistency with existing tree beats
   any system's individual merit.
2. **System domain expects or requires.** Some platforms and sectors
   effectively mandate one; anything else feels foreign or fails compliance
   expectation.
3. **Foundation you extend**, when brand expression is differentiator but
   component behavior is not.
4. **Hand-composed**, most expensive option: choose only when visual
   identity is itself product and is the reason.

## Matching a brief to a foundation

| Brief reads as | Reach for |
| --- | --- |
| Microsoft-adjacent or enterprise productivity | Fluent |
| Android-adjacent or Material-flavored product | Material |
| Enterprise analytics with dense data | Carbon |
| App surface inside commerce platform's admin | That platform's own system, usually required |
| Atlassian-adjacent product surface | Atlassian's system |
| Developer tooling or code-hosting community surface | Primer, with its brand variant for marketing |
| UK public-sector service | GOV.UK Frontend, effectively expected |
| US federal or civic service | US Web Design System |
| Accessible unstyled foundation, own visual layer | Headless primitive library plus your own tokens |
| Modern product where you want to own component source | Copy-in component collection, always customized |
| Fast conventional build, no brand ambition | Established general-purpose framework |

Before installing, verify current package name, version, installation
procedure from system's own documentation; package names, entry points,
framework support change.

## Rules

* **One system per tree.** Mixing two inherits constraints of both,
  coherence of neither.
* **Use it or replace it.** Overriding large share of system's tokens means
  wrong system chosen. Report mismatch; change decision.
* **Theme through intended mechanism**: system's own theming layer, set once
  at application root. Overrides break on upgrade.
* **Customize copy-in components before shipping.** At default values they
  produce recognizable unmodified look. Adapt radii, spacing, type, color to
  project's tokens.
* **Read system's own guidance** before composing with it. Most encode
  decisions about density, elevation, motion that hand-composed layout will
  contradict.

## Aesthetics are not systems

These visual directions have no official package. Implement with platform
primitives; describe accurately.

| Direction | Honest implementation |
| --- | --- |
| Frosted or translucent material | Backdrop filtering, layered borders, highlight overlays |
| Tile grids of mixed sizes | Grid with varied cell spans; no library owns this |
| Brutalist | Native elements, monospace, unornamented borders |
| Editorial | Type, asymmetric grid, space; no library |
| Terminal or hacker | Monospace with restrained accent |
| Mesh or aurora backgrounds | Layered gradients or vector art, on non-interactive layer |
| Kinetic type | CSS animation and scroll-linked timelines |

Any translucent material needs solid, high-contrast fallback preserving
contrast when transparency reduced or unsupported. Proprietary platform's
named material is documented by its vendor for that vendor's platforms; web
build of it is approximation, must be labeled as one in code comments, must
not be presented to user as real system.
